import base64
import datetime

import xlwt
from six import BytesIO
from xlsxwriter.utility import xl_rowcol_to_cell

from odoo import models, fields
from odoo.exceptions import MissingError
from . import arial10


class ReportFinancial(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def get_account_lines(self, data):
        report_name = data['account_report_id'][1].lower()
        is_consolidate = "consolidation" in report_name.lower()
        companies = self.env.company + self.env.company.child_ids
        if not is_consolidate:
            return super(ReportFinancial, self).get_account_lines(data)
        consolidate_report = self.env['account.financial.report'].search([('id', '=', data['account_report_id'][0])])
        data['used_context']['company_id'] = False
        data['used_context']['allowed_company_ids'] = companies.ids
        lines = []
        child_reports = consolidate_report._get_children_by_order()
        res = self.with_context(data.get('used_context'))._compute_report_balance(child_reports)
        if data['enable_filter']:
            comparison_res = self.with_context(data.get('comparison_context'))._compute_report_balance(child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']
        for report in child_reports:
            vals = {
                'name': report.name,
                'preserve_sign': float(report.sign) > 0,
                'balance': res[report.id]['balance'] * float(report.sign),
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'acc_lvl': report.level,
                'account_type': report.type or False,  # used to underline the financial report balances
                'parent_report': report.parent_id.name
            }
            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * float(report.sign)

            lines.append(vals)
            if report.display_detail == 'no_detail':
                # the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    # if there are accounts to display, we add them to the lines with a level equals to their level in
                    # the COA + 1 (to avoid having them with a too low level that would conflict with the level of data
                    # financial reports for Assets, liabilities...)
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'name': account.name,
                        'preserve_sign': float(report.sign) > 0,
                        'balance': value['balance'] * float(report.sign) or 0.0,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and 4,
                        'acc_lvl': report.level + 1,
                        'account_type': account.internal_type,
                        'company_name': account.company_id.name,
                        'parent_report': report.name
                    }
                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not account.company_id.currency_id.is_zero(
                                vals['debit']) or not account.company_id.currency_id.is_zero(vals['credit']):
                            flag = True
                    if not account.company_id.currency_id.is_zero(vals['balance']):
                        flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * float(report.sign)
                        if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
                            flag = True
                    if flag:
                        sub_lines.append(vals)
                lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])
        return lines


class AccountFinancialReport(models.TransientModel):
    _inherit = "accounting.report"
    workbook = None
    worksheet = None
    sum_accs = dict()
    table_rows = list()
    table_columns = list()
    company_columns = list()
    company_to_eliminate = list()
    reversed_sign_account = list()

    account_name_style = xlwt.XFStyle()
    table_header_style = xlwt.XFStyle()
    account_balance_style = xlwt.XFStyle()
    sum_account_balance_style = xlwt.XFStyle()

    # Utility Function
    def _cells_to_ranges(self, cells, sum_row=True):
        result = list()
        while cells:
            cell_coord = cells.pop(0)
            cell_range = [cell_coord]
            new_coord = (cell_coord[0] + 1, cell_coord[1])
            if new_coord not in cells:
                result.append(xl_rowcol_to_cell(*cell_coord))
                continue
            while new_coord in cells:
                cells.remove(new_coord)
                if len(cell_range) == 2:
                    cell_range[1] = new_coord
                else:
                    cell_range.append(new_coord)
                new_coord = (new_coord[0] + 1, new_coord[1])
            result.append(":".join([xl_rowcol_to_cell(*cr) for cr in cell_range]))
        return result

    def _do_elimination(self, journal_item, account_rows):
        account_row = journal_item.account_id.name + journal_item.company_id.name
        partner = journal_item.partner_id
        to_eliminate = journal_item.move_id.to_eliminate

        # check if journal item not in the report
        if account_row not in account_rows:
            return False
        # condition when there is no specified partner in journal item
        if not partner and not to_eliminate:
            return False
        # condition when there is a specified partner in journal item
        if partner.can_do_elimination() or to_eliminate:
            return journal_item
        else:
            return False

    def _get_account_to_eliminate(self, data):
        date_from = fields.Date.from_string(data['form']['date_from'])
        date_to = fields.Date.from_string(data['form']['date_to'])
        target_move = data['form']['target_move']
        domain = ['&', ('date', '>=', date_from) if date_from else (1, '=', 1),
                  ('date', '<=', date_to) if date_to else (1, '=', 1), ('parent_state', '=', target_move)]
        account_move_lines = self.env['account.move.line'].search(domain)
        account_to_eliminate = {}
        for journal_item in account_move_lines:
            account = journal_item.account_id.name
            company = journal_item.company_id.name
            journal_item = self._do_elimination(journal_item, self.table_rows)
            if not journal_item:
                continue
            account_to_eliminate[account + company] = account_to_eliminate.get(account, {})
            account_to_eliminate[account + company] = {
                'balance': account_to_eliminate[account + company].get('balance', 0) + journal_item.balance,
                'company': company
            }
        return account_to_eliminate

    def _get_consolidation_account_lines(self, data):
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        account_lines = self.env['report.accounting_pdf_reports.report_financial'].get_account_lines(data=data['form'])
        account_lines.pop(0)
        has_transaction = False
        for line in account_lines:
            if not has_transaction and line.get('company_name', False):
                has_transaction = True
        if not has_transaction:
            raise MissingError("There is no transaction found.")
        return account_lines

    def _expand_col(self, col, val, worksheet=None):
        worksheet = worksheet or self.worksheet
        if type(val) == xlwt.Formula:
            worksheet.col(col).set_width(256 * 20)
            return
        width = arial10.fitwidth(str(val), True)
        default_width = worksheet.col(col).width
        if width > default_width:
            worksheet.col(col).set_width(int(width))

    def _set_table_header_style(self):
        alignment = xlwt.Alignment()
        alignment.horz = alignment.HORZ_CENTER
        alignment.vert = alignment.VERT_CENTER

        font = xlwt.Font()
        font.bold = True

        self.table_header_style.alignment = alignment
        self.table_header_style.font = font

    def _set_account_name_style(self):
        alignment = xlwt.Alignment()
        alignment.vert = alignment.VERT_CENTER

        font = xlwt.Font()
        font.bold = True

        self.account_name_style.alignment = alignment
        self.account_name_style.font = font

    def _set_account_balance_style(self):
        alignment = xlwt.Alignment()
        alignment.horz = alignment.HORZ_RIGHT
        alignment.vert = alignment.VERT_CENTER

        self.account_balance_style.alignment = alignment
        self.account_balance_style.num_format_str = "[$$-409]#,##0.00;-[$$-409]#,##0.00"

    def _set_sum_account_balance_style(self):
        alignment = xlwt.Alignment()
        alignment.horz = alignment.HORZ_RIGHT
        alignment.vert = alignment.VERT_CENTER

        font = xlwt.Font()
        font.bold = True

        self.sum_account_balance_style.alignment = alignment
        self.sum_account_balance_style.font = font
        self.sum_account_balance_style.num_format_str = "[$$-409]#,##0.00;-[$$-409]#,##0.00"

    def _setup_styles(self):
        borders = xlwt.Borders()
        borders.left = borders.right = borders.bottom = borders.top = borders.THIN
        self._set_table_header_style()
        self._set_account_name_style()
        self._set_account_balance_style()
        self._set_sum_account_balance_style()
        self.table_header_style.borders = \
            self.account_name_style.borders = \
            self.account_balance_style.borders = \
            self.sum_account_balance_style.borders = borders

    def _write_table_header(self, row, col, val, worksheet=None):
        worksheet = worksheet or self.worksheet
        self._expand_col(col, val, worksheet)
        return worksheet.write(row, col, val, self.table_header_style)

    def _write_account_name(self, row, col, val, worksheet=None):
        worksheet = worksheet or self.worksheet
        self._expand_col(col, val, worksheet)
        worksheet.row(row).height = 500
        return worksheet.write(row, col, val, self.account_name_style)

    def _write_account_balance(self, row, col, val, worksheet=None):
        worksheet = worksheet or self.worksheet
        self._expand_col(col, val, worksheet)
        return worksheet.write(row, col, val, self.account_balance_style)

    def _write_sum_account_balance(self, row, col, val, worksheet=None):
        worksheet = worksheet or self.worksheet
        self._expand_col(col, val, worksheet)
        return worksheet.write(row, col, val, self.sum_account_balance_style)

    def _write_balancesheet(self, account_lines):
        for line in account_lines:
            account = line['name']
            company = line.get('company_name', '')
            row_label = account + company
            row = len(self.table_rows)
            # Note down all the accounts for each report so that we can add SUM formula later
            if line['type'] == 'report':
                self.sum_accs[account] = []
                self.sum_accs[line['parent_report']] = self.sum_accs.get(line['parent_report'], []) + [row_label]
            else:
                self.sum_accs[line['parent_report']].append(row_label)
            # Note down the column of each companies
            if company and (company not in self.table_columns):
                self.table_columns.append(company)
                self.company_columns.append(company)
                self._write_table_header(self.table_rows.index("Account Name"), self.table_columns.index(company),
                                         company)
            if line['type'] == 'report':  # line type is report (type: report don't have company_name key)
                self._write_account_name(row, 0, "  " * line["acc_lvl"] + account)
            else:  # line type is account
                self._write_account_name(row, 0, "  " * line["acc_lvl"] + account)
                self._write_account_balance(row, self.table_columns.index(company), line['balance'])
            # Note the account with reverse sign
            if not line['preserve_sign']:
                self.reversed_sign_account.append(row_label)
            self.table_rows.append(row_label)

    # CJE: Consolidated Journal Entries
    def _write_balance_before_cje(self):
        self._write_table_header(self.table_rows.index("Account Name"), len(self.table_columns), "Before CJE")
        self.table_columns.append("Before CJE")
        starting_row = self.table_rows.index("Account Name") + 1
        ending_row = len(self.table_rows)
        for r in range(starting_row, ending_row):
            sum_cell = []
            for col in self.company_columns:
                c = self.table_columns.index(col)
                sum_cell.append(xl_rowcol_to_cell(r, c))
            formula_value = "SUM(" + ",".join(sum_cell) + ")"
            self._write_sum_account_balance(r, self.table_columns.index("Before CJE"), xlwt.Formula(formula_value))

    def _write_elimination(self, account_to_eliminate):
        for row_label, line in account_to_eliminate.items():
            company = line['company']
            balance = line['balance'] * (-1 if row_label in self.reversed_sign_account else 1)
            eliminate_company = 'Eliminate-' + company
            if eliminate_company not in self.company_to_eliminate:
                self.company_to_eliminate.append(eliminate_company)
                self.table_columns.append(eliminate_company)
                self._write_table_header(self.table_rows.index("Account Name"),
                                         self.table_columns.index(eliminate_company),
                                         company)
            self._write_account_balance(self.table_rows.index(row_label),
                                        self.table_columns.index(eliminate_company),
                                        balance)

    def _write_balance_after_cje(self):
        if not self.company_to_eliminate:
            return
        self._write_table_header(self.table_rows.index("Account Name"), len(self.table_columns), "After CJE")
        self.table_columns.append("After CJE")
        starting_row = self.table_rows.index("Account Name") + 1
        ending_row = len(self.table_rows)
        for r in range(starting_row, ending_row):
            sum_cell = []
            for col in self.company_to_eliminate:
                c = self.table_columns.index(col)
                sum_cell.append(xl_rowcol_to_cell(r, c))
            before_cje_cell = xl_rowcol_to_cell(r, self.table_columns.index("Before CJE"))
            formula_value = before_cje_cell + " - SUM(" + ",".join(sum_cell) + ")"
            self._write_sum_account_balance(r, self.table_columns.index("After CJE"), xlwt.Formula(formula_value))

    def _write_sum_acc_formula(self):
        sum_cols = self.company_columns + self.company_to_eliminate
        sum_col_index = [self.table_columns.index(col) for col in sum_cols]
        for sum_acc, child_accs in self.sum_accs.items():
            if sum_acc not in self.table_rows:
                continue
            sum_acc_row = self.table_rows.index(sum_acc)
            for col in sum_col_index:
                sum_cell = []
                for child_acc in child_accs:
                    child_acc_row = self.table_rows.index(child_acc)
                    sum_cell.append((child_acc_row, col))
                sum_cell = self._cells_to_ranges(sum_cell)
                if sum_cell:
                    formula_value = "SUM(" + ",".join(sum_cell) + ")"
                    self._write_account_balance(sum_acc_row, col, xlwt.Formula(formula_value))
                else:
                    self._write_account_balance(sum_acc_row, col, 0)

    def _write_default_balance(self):
        start_row = self.table_rows.index("Account Name")
        start_col = self.table_columns.index("Account Name")
        end_row = len(self.table_rows)
        end_col = len(self.table_columns)
        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                try:
                    self._write_account_balance(row, col, 0)
                except Exception as e:
                    pass

    def _consolidation_recap_report(self):
        if not self.company_to_eliminate:
            return
        recap_sheet = self.workbook.add_sheet("Recap Consolidation")
        sum_acc_name = [line for line in self.sum_accs.keys() if line in self.table_rows]
        consolidation_sheet = self.worksheet
        table_rows = list()
        report_line = list()
        for acc, child in self.sum_accs.items():
            if acc in sum_acc_name:
                report_line.append(acc)
                sum_acc_name.remove(acc)
            for child_acc in child:
                if child_acc in sum_acc_name:
                    if acc in report_line:
                        report_line.insert(report_line.index(acc) + 1, child_acc)
                    else:
                        report_line.append(child_acc)
                    sum_acc_name.remove(child_acc)
        for line in report_line:
            account_name_cell_ref = xl_rowcol_to_cell(self.table_rows.index(line),
                                                      self.table_columns.index("Account Name"))
            account_balance_cell_ref = xl_rowcol_to_cell(self.table_rows.index(line),
                                                         self.table_columns.index("After CJE"))
            account_name = f"'{consolidation_sheet.name}'!{account_name_cell_ref}"
            account_balance_cell = f"'{consolidation_sheet.name}'!{account_balance_cell_ref}"
            account_balance = f"IF({account_balance_cell}=0, \"\",{account_balance_cell})"
            self._write_account_name(len(table_rows), 0, xlwt.Formula(account_name), worksheet=recap_sheet)
            self._write_account_balance(len(table_rows), 1, xlwt.Formula(account_balance), worksheet=recap_sheet)
            recap_sheet.col(0).set_width(10000)
            recap_sheet.col(1).set_width(5000)
            table_rows.append(line)

    def _consolidation_report_xlsx(self, data):
        self.company_columns = []
        # ["'Eliminate-'+company"]
        self.company_to_eliminate = []
        row, column = 0, 0

        self.workbook = xlwt.Workbook(encoding="UTF-8")
        self.worksheet = self.workbook.add_sheet(data['form']['account_report_id'][1])
        self._setup_styles()

        self.worksheet.row(1).height = 500

        # Header
        self.worksheet.write(row, column, str(datetime.date.today()))
        row += 1
        self._write_table_header(row, column, "Account Name")

        # ['account+company']
        self.table_rows = ['-'] * row
        # ['company']
        self.table_columns = ['-'] * column
        self.table_columns.append("Account Name")
        self.table_rows.append("Account Name")

        account_lines = self._get_consolidation_account_lines(data)
        self._write_balancesheet(account_lines)
        self._write_balance_before_cje()

        account_to_eliminate = self._get_account_to_eliminate(data)
        self._write_elimination(account_to_eliminate)
        self._write_balance_after_cje()

        self._write_sum_acc_formula()
        self._write_default_balance()

        self._consolidation_recap_report()

        fp = BytesIO()
        self.workbook.save(fp)
        self.financial_report_excel_file = base64.encodebytes(fp.getvalue())
        fp.close()

        # __________________________________________#
        #   Return the URL to download the report   #
        # __________________________________________#

        return {
            'type': 'ir.actions.act_url',
            'name': 'Financial Consolidation Report ',
            'url': '/web/content/accounting.report/%s/financial_report_excel_file/'
                   f'{data["form"]["account_report_id"][1]}.xls?download=true' % (
                       self.id),
        }

    def _print_report_xlsx(self, data):
        data['form'].update(self.read(['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
                                       'account_report_id', 'enable_filter', 'label_filter', 'target_move'])[0])
        report_name = data['form']['account_report_id'][1].lower()
        is_consolidate = "consolidation" in report_name.lower()
        if not is_consolidate:
            return super(AccountFinancialReport, self)._print_report_xlsx(data)
        else:
            try:
                return self._consolidation_report_xlsx(data)
            except MemoryError as me:
                raise MissingError("The report is too large to process. Please narrow down the date range.")
