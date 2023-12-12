from pprint import pprint
from odoo import models, api
import json


class VkrPaymentVoucher(models.AbstractModel):
    _inherit = "account.move"

    ###################################################################
    # - inherit data from account.move                                #
    # - write a function to get data through payment widget           #
    # - getting data from aacount.move.line, account.payment          #
    # - write function to calculate and get data for debit, credits   #
    #   for account payable row                                       #
    ###################################################################

    # for payment widget
    def get_vendor_bill_data(self, payments_widget):
        if payments_widget == 'false':
            return
        content = json.loads(payments_widget)
        payment_object = dict()
        for item in content['content']:
            # Getting payment bill data
            payment_table = self.env['account.move.line'].browse([item['payment_id'], item['payment_id'] + 1])
            payment_ref = self.env['account.move.line'].browse(item['payment_id'] + 1).name
            invoice_ref = self.env['account.payment'].search([('name', '=', payment_ref)]).communication
            memo = self.env['account.payment'].search([('name', '=', payment_ref)]).memo_payment

            date_reformat = item['date'][-2:] + "/" + item['date'][5:7] + "/" + item['date'][0:4]

            for data_payment in payment_table:
                if payment_ref not in payment_object:
                    payment_object[payment_ref] = {
                        'label': [data_payment.name],
                        'journal': [item['journal_name']],
                        'debit': [data_payment.debit],
                        'credit': [data_payment.credit],
                        'partner': [data_payment.partner_id.name],
                        'account_code': [data_payment.account_id.code],
                        'account_name': [data_payment.account_id.name],
                        'date': date_reformat,
                        'amount': [round(item['amount'], 2)],
                        'remark': [item['ref']],
                        'analytic_acc': [data_payment.analytic_account_id.name],
                        'memo': [memo],
                        'invoice_ref': [invoice_ref],
                    }
                else:
                    payment_object[payment_ref]['label'].append(data_payment.name)
                    payment_object[payment_ref]['journal'].append(item['journal_name'])
                    payment_object[payment_ref]['debit'].append(data_payment.debit)
                    payment_object[payment_ref]['credit'].append(data_payment.credit)
                    payment_object[payment_ref]['partner'].append(data_payment.partner_id.name)
                    payment_object[payment_ref]['account_code'].append(data_payment.account_id.code)
                    payment_object[payment_ref]['account_name'].append(data_payment.account_id.name)
                    payment_object[payment_ref]['amount'].append(round(item['amount'], 2))
                    payment_object[payment_ref]['remark'].append(item['ref'])
                    payment_object[payment_ref]['analytic_acc'].append(data_payment.analytic_account_id.name)
                    payment_object[payment_ref]['memo'].append(memo)
                    payment_object[payment_ref]['invoice_ref'].append(invoice_ref)

        return payment_object

    # to get total of debit and credit and account payable
    def get_total_of_payment_voucher(self):
        total_debit = 0
        for value in self.line_ids:
            total_debit += value.debit

        return total_debit

    # for acc payable
    def _get_account_payable(self):
        total_credit = 0
        for line in self.line_ids:
            total_credit += line.credit
            if line.account_id.user_type_id.name == 'Accounts Payable':
                return line, total_credit
        return False, total_credit

    class ReportPDF(models.AbstractModel):
        _name = "report.a2a_accounting_report.payment_voucher_pdf1"

        @api.model
        def _get_report_values(self, docids, data=None):
            docs = self.env['account.move'].browse(docids)
            journal_items = {}

            for doc in docs:
                account_payable = dict()
                vat_input = dict()
                journal_items[doc.id] = {}
                is_paid = doc.state == 'posted' and doc.invoice_payment_state == 'paid'
                for line in doc.line_ids:
                    if line.account_id.user_type_id.name == 'Accounts Payable' and is_paid:
                        continue

                    bill_data = {
                        'date': line.date,
                        'product_name_in_journal_entries': line.name,
                        'account_name': line.account_id.name,
                        'product_name': line.product_id.product_tmpl_id.name,
                        'quantity': line.quantity,
                        'unit_name': line.product_uom_id['name'],
                        'debit': line.debit,
                        'credit': line.credit,
                    }
                    code = line.account_id.code

                    if "VAT" in line.account_id.name:
                        vat_input[code] = bill_data
                        continue
                    if line.account_id.user_type_id.name == 'Accounts Payable':
                        account_payable[code] = bill_data
                        continue
 
                    if code not in journal_items[doc.id]:
                        journal_items[doc.id][code] = bill_data
                    else:
                        # Check if there are more than 5 items for the product_name
                        if len(journal_items[doc.id][code]['product_name'].split(', ')) < 5:
                            # If less than 5, append the new product_name
                            journal_items[doc.id][code]['product_name'] += ', ' + bill_data['product_name']
                        else:
                            if '...' in journal_items[doc.id][code]['product_name'].split(', '):
                                pass
                            else:
                                journal_items[doc.id][code]['product_name'] += ', ...'
                        journal_items[doc.id][code]['quantity'] += bill_data['quantity']
                        journal_items[doc.id][code]['debit'] += bill_data['debit']
                        journal_items[doc.id][code]['credit'] += bill_data['credit']

                journal_items[doc.id].update(vat_input)
                journal_items[doc.id].update(account_payable)


            for journal in journal_items:
                sorted_journal_items = dict(
                    sorted(journal_items[journal].items(), key=lambda item: item[1]['credit'], reverse=False))
                journal_items[journal] = sorted_journal_items
            
            return {
                'doc_ids': docids,
                'data': data,
                'docs': docs,
                'journal_items': journal_items
            }

    class ReportVkrPDF(models.AbstractModel):
        _name = "report.a2a_accounting_report.vkr_payment_voucher_pdf"
        _inherit = "report.a2a_accounting_report.payment_voucher_pdf1"
