import base64
import copy
import datetime

import xlwt
from odoo.addons.accounting_pdf_reports.reports.report_financial import ReportFinancial
from six import BytesIO

from odoo import models


class CustomizeFinancialAccountLineHierarchy(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _get_beginning_balance(self, journal_entries_ids, reversed_sign_accs):
        acc_beginning_bal = dict()
        journal_entries = self.env["account.move"].search(
            [('id', 'in', journal_entries_ids)])
        for journal_entry in journal_entries:
            for line in journal_entry.line_ids:
                key = line.account_id.code + " " + line.account_id.name
                sign = -1 if key in reversed_sign_accs else 1
                acc_beginning_bal[key] = acc_beginning_bal.get(key, 0) + sign * line.balance
        return acc_beginning_bal

    def get_variance(self, data, beginning_balance):
        if 'balance_cmp' not in data[0]:
            return data
        acc_parent = [(0, 0)]
        data[0]['variance'] = 0
        level = 0
        for i in range(1, len(data)):
            data[i]['variance'] = data[i].get('variance', 0)
            acc_name = data[i]['name']
            if acc_name in beginning_balance:
                data[i]["balance"] -= beginning_balance[acc_name]
            if data[i]['type'] == 'account':
                # level = int(data[i]['level'])
                code = data[i]['name'].split()[0]
                acc = self.env['account.account'].search([('code', '=', code)])
                sign = 1 if acc.cashflow_logic == 'new_old' else -1
                sign = 1 if acc.cashflow_logic not in [
                    'new_old', 'old_new'] else sign
                data[i]['variance'] = sign * \
                                      (data[i]['balance'] - data[i]['balance_cmp'])
                for index, l in acc_parent:
                    data[index]['variance'] += data[i]['variance']
            else:
                if data[i]['name'] == 'Adjustment':
                    continue
                # check the current row has no child
                if i + 1 < len(data):

                    if int(data[i]['level']) == int(data[i + 1]['level']):

                        data[i]['variance'] = data[i]['balance'] - \
                                              data[i]['balance_cmp']
                        for index, l in acc_parent:
                            data[index]['variance'] += data[i]['variance']
                        continue

                # check if the current row is the child of the previous row
                if int(data[i]['level']) > level:
                    level = int(data[i]['level'])
                    acc_parent.append((i, level))
                # traverse back or exit from the parent
                else:
                    acc_parent = [x for x in acc_parent if x[1]
                                  < int(data[i]['level'])]
                    level = int(data[i]['level'])
                    acc_parent.append((i, level))
                    # if this is the last row
                    if i == len(data) - 1:
                        data[i]['variance'] = data[i]['balance'] - \
                                              data[i]['balance_cmp']
                        acc_parent.pop()
                        for index, l in acc_parent:
                            data[index]['variance'] += data[i]['variance']
        return data

    def total_cash_flows(self, data):
        net_increase = sum([x['variance']
                            for x in data if int(x['level']) == 1])
        cash_beginning = data[-1]['balance_cmp']

        cash_ending = net_increase + cash_beginning
        data.pop()
        data.append({'name': 'Net increase in cash and cash equivalents',
                     'balance': -1,
                     'type': 'report',
                     'level': 1,
                     'account_type': 'sum',
                     'balance_cmp': -1,
                     'variance': net_increase})
        data.append({'name': 'Cash and cash equivalents at beginning of period',
                     'balance': -1,
                     'type': 'report',
                     'level': 1,
                     'account_type': 'sum',
                     'balance_cmp': -1,
                     'variance': cash_beginning})
        data.append({'name': 'Cash and cash equivalents at end of period',
                     'balance': -1,
                     'type': 'report',
                     'level': 1,
                     'account_type': 'sum',
                     'balance_cmp': -1,
                     'variance': cash_ending})

        return data

    def _get_revers_sign_accs(self, data):
        accs = list()
        account_report = self.env['account.financial.report'].search([('id', '=', data['account_report_id'][0])])
        child_reports = account_report._get_children_by_order()
        res = self.with_context(data.get('used_context'))._compute_report_balance(child_reports)
        for report in child_reports:
            if res[report.id].get('account'):
                for account_id, value in res[report.id]['account'].items():
                    account = self.env['account.account'].browse(account_id)
                    acc_name = account.code + ' ' + account.name
                    if float(report.sign) < 0:
                        accs.append(acc_name)
        return accs

    def get_account_lines(self, data):
        account_report = self.env['account.financial.report'].search(
            [('id', '=', data['account_report_id'][0])])
        data['statement_of_cashflow_report_id'] = self.env.ref(
            'a2a_statement_of_cashflow.account_financial_report_cashflows').id
        reversed_sign_accs = self._get_revers_sign_accs(data)
        beginning_balance = self._get_beginning_balance(data['beginning_journal_entries_ids'], reversed_sign_accs)
        if not account_report.show_parent:
            res = ReportFinancial.get_account_lines(self, data)
            res = self.get_variance(res, beginning_balance)

            if account_report.id == data['statement_of_cashflow_report_id']:
                res = self.total_cash_flows(res)
            return res
        res = super(CustomizeFinancialAccountLineHierarchy,
                    self).get_account_lines(data)
        res = self.get_variance(res, beginning_balance)
        if account_report.id == data['statement_of_cashflow_report_id']:
            res = self.total_cash_flows(res)
        return res


class AccountFinancialReportXlsx(models.TransientModel):
    _inherit = "accounting.report"

    def _print_report(self, data):
        data['form']['beginning_journal_entries_ids'] = self.beginning_balance.ids
        return super(AccountFinancialReportXlsx, self)._print_report(data)

    def _print_report_xlsx(self, data):
        """
        Arguments: Data(Passed from get account line and check report function
        For print Excel report for Financial report
            Steps:
            + Grab the data for inserting into the excel
            + Create and Style the excel
            + Set condition for each filter
            + Return the url to download the excel file

        """
        data['form']['beginning_journal_entries_ids'] = self.beginning_balance.ids
        cashflow_report_ref = self.env.ref(
            'a2a_statement_of_cashflow.account_financial_report_cashflows').id

        if self.read(['account_report_id'])[0]['account_report_id'][0] != cashflow_report_ref:
            return super(AccountFinancialReportXlsx, self)._print_report_xlsx(data)
        data['form'].update(self.read(['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
                                       'account_report_id', 'enable_filter', 'label_filter', 'target_move'])[0])
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        account_line = self.env['report.accounting_pdf_reports.report_financial'].get_account_lines(
            data=data['form'])
        currency = self.env.company.currency_id

        # Create the worksheet
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet(data['form']['account_report_id'][1])
        worksheet.col(0).width = 256 * 40
        worksheet.col(1).width = 256 * 20
        worksheet.col(2).width = 256 * 20
        worksheet.col(3).width = 256 * 20
        worksheet.col(4).width = 256 * 20
        worksheet.row(1).height = 500
        # Styling
        header_style = xlwt.easyxf(
            'font:height 200; align: horiz center, vert center;')
        title_style = xlwt.easyxf(
            'font:height 400,  bold True; align: horiz left, vert center; ')
        sub_header_style = xlwt.easyxf(
            'font:height 200, bold True;align: horiz left, vert center;')
        sub_header_input_style = xlwt.easyxf(
            'font:height 200;align: horiz left, vert center;')
        data_header_name_style = xlwt.easyxf('font:height 200,  bold True; align: horiz left, vert center'
                                             '; borders: right_color black, left_color black,top_color black'
                                             ', bottom_color black, right thin, left thin, bottom thin, top thin;')
        data_header_style = xlwt.easyxf('font:height 200, bold True;align: vert top, horiz center, vert center; '
                                        'borders: right_color black, left_color black, top_color black'
                                        ',bottom_color black, right thin, left thin,bottom thin, top thin;')
        data_of_transaction_bold = copy.deepcopy(data_header_style)
        data_of_transaction_bold.alignment.horz = 1
        data_of_transaction_bold.num_format_str = currency.symbol + " 0.00"
        data_of_transaction_bold_right = copy.deepcopy(
            data_of_transaction_bold)
        data_of_transaction_bold_right.alignment.horz = 3
        # font size calculation 16 * 20, for 16 point
        data_of_transaction_bold_right.font.height = 220
        data_of_transaction_style = copy.deepcopy(data_of_transaction_bold)
        data_of_transaction_style.font.bold = False
        data_of_transaction_style.alignment.horz = 1
        leaf_node = xlwt.easyxf('font:height 200; align: horiz left, vert center; '
                                'borders: right_color black, left_color black,top_color black,'
                                'bottom_color black, right thin, left thin, bottom thin, top thin;')

        # Header
        worksheet.write(0, 0, str(datetime.date.today()),
                        sub_header_input_style)
        # Target Move
        worksheet.write(3, 0, 'Target Moves: ', sub_header_style)
        if data['form']['target_move'] == 'all':
            worksheet.write(4, 0, 'All Entries ', sub_header_input_style)
        elif data['form']['target_move'] == 'posted':
            worksheet.write(4, 0, 'All Posted Entries', sub_header_input_style)
            # Date From & To
        if data['form']['date_from'] is not False:
            worksheet.write(
                3, 1, 'Date From: ' + str(data['form']['date_from']), sub_header_input_style)
        if data['form']['date_to'] is not False:
            worksheet.write(
                4, 1, 'Date to: ' + str(data['form']['date_to']), sub_header_input_style)
        row = 5
        # condition for selected Debit_Credit check box
        if data['form']['debit_credit'] == 1:
            worksheet.write_merge(
                0, 0, 1, 3, data['form']['company_id'][1], header_style)
            worksheet.write_merge(
                1, 1, 0, 3, data['form']['account_report_id'][1], title_style)
            worksheet.write(row, 0, 'Name', data_header_name_style)
            worksheet.write(row, 1, 'Debit', data_header_style)
            worksheet.write(row, 2, 'Credit', data_header_style)
            worksheet.write(row, 3, 'Balance', data_header_style)
            for line in account_line:
                if line['level'] != 0:
                    row += 1
                    worksheet.write(row, 0, "  " * int(line.get("level")) + line.get('name'),
                                    leaf_node if line.get('type') == 'account' else data_header_name_style)

                    worksheet.write(row, 1, line.get('debit'),
                                    data_of_transaction_style if line.get('type') == 'account'
                                    else data_of_transaction_bold)
                    worksheet.write(row, 2, line.get('credit'),
                                    data_of_transaction_style if line.get('type') == 'account'
                                    else data_of_transaction_bold)
                    worksheet.write(row, 3, line.get('balance'),
                                    data_of_transaction_style if line.get('type') == 'account'
                                    else data_of_transaction_bold)

        # condition without select any check box
        elif not data['form']['enable_filter'] and not data['form']['debit_credit']:
            worksheet.write_merge(
                0, 0, 1, 1, data['form']['company_id'][1], header_style)
            worksheet.write_merge(
                1, 1, 0, 1, data['form']['account_report_id'][1], title_style)
            worksheet.write(row, 0, 'Name', data_header_name_style)
            worksheet.write(row, 1, 'Balance', data_header_style)
            for line in account_line:
                if line['level'] != 0:
                    row += 1
                    worksheet.write(row, 0, "  " * int(line.get("level")) + line.get('name'),
                                    leaf_node if line.get('type') == 'account' else data_header_name_style)
                    worksheet.write(row, 1, line.get('balance'),
                                    data_of_transaction_style if line.get('type') == 'account'
                                    else data_of_transaction_bold)

        # Condition for selected Enable Comparison
        elif data['form']['enable_filter'] and not data['form']['debit_credit']:
            worksheet.write_merge(
                0, 0, 1, 2, data['form']['company_id'][1], header_style)
            worksheet.write_merge(
                1, 1, 0, 2, data['form']['account_report_id'][1], title_style)
            worksheet.write(row, 0, 'Name', data_header_name_style)
            # worksheet.write(row, 1, 'Balance', data_header_style)
            # worksheet.write(row, 2, data['form']['label_filter'], data_header_style)
            worksheet.write(row, 1, 'Variance', data_header_style)

            for index, line in enumerate(account_line):

                if line['level'] != 0:
                    row += 1
                    style_bold = data_of_transaction_bold
                    parent_name_style = data_header_name_style
                    if int(line['level']) == 1:
                        style_bold = data_of_transaction_bold_right
                    if index > len(account_line) - 4:
                        parent_name_style = data_of_transaction_bold_right
                    if line.get('name') == 'Adjustment':
                        worksheet.write_merge(
                            row, row, 0, 1, "Adjustment", parent_name_style)
                        continue
                    worksheet.write(row, 0, "  " * int(line.get("level")) + line.get('name'),
                                    leaf_node if line.get('type') == 'account' else parent_name_style)

                    # worksheet.write(row, 1, line.get('balance'),
                    #                 data_of_transaction_style if line.get('type') == 'account'
                    #                 else data_of_transaction_bold)
                    # worksheet.write(row, 2, line.get('balance_cmp'),
                    #                 data_of_transaction_style if line.get('type') == 'account'
                    #                 else data_of_transaction_bold)

                    worksheet.write(row, 1, line.get('variance'),
                                    data_of_transaction_style if line.get('type') == 'account'
                                    else style_bold)

        fp = BytesIO()
        workbook.save(fp)
        self.financial_report_excel_file = base64.encodebytes(fp.getvalue())
        fp.close()

        # __________________________________________#
        #   Return the URL to download the report   #
        # __________________________________________#

        return {
            'type': 'ir.actions.act_url',
            'name': 'Financial Report',
            'url': '/web/content/accounting.report/%s/financial_report_excel_file/'
                   f'{data["form"]["account_report_id"][1]}.xls?download=true' % (
                       self.id),
        }
