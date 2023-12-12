from odoo import fields, api, models
from datetime import datetime


class CustomerAgingWizard(models.TransientModel):
    _name = "account.move.customer.aging.wizard"
    
    aging_date = fields.Date(string='Aging Date')
    def action_compute_customer_aging(self):
        domain = [('type', '=', 'out_invoice'), ('state', '=', 'posted'), ('invoice_payment_state', '!=', 'paid')]
        invoices = self.env['account.move'].search(domain)
        for invoice in invoices:
            age = (self.aging_date - invoice.invoice_date_due).days if self.aging_date > invoice.invoice_date_due else 0
            invoice.age = age

        return {
        'name': 'Customer Aging',
        'view_mode': 'tree,form',
        'views': [
            (self.env.ref('accounting_customer_aging.customer_aging_list_view').id, 'tree'),
            (self.env.ref('account.view_move_form').id, 'form'),
        ],
        'res_model': 'account.move',
        'domain': domain,
        'type': 'ir.actions.act_window',
        'target': 'current',
    }
    
    def action_print_excel_report(self):

        data = {}

        domain = [('type', '=', 'out_invoice'), ('state', '=', 'posted'), ('invoice_payment_state', '!=', 'paid')]

        invoice_list = self.env['account.move'].search(domain)
        for invoice in invoice_list:
            invoice.age = (self.aging_date - invoice.invoice_date_due).days if self.aging_date > invoice.invoice_date_due else 0
        
        # Step 1: Get Unique Sets of customer

        unique_customers = set(invoice['invoice_partner_display_name'] for invoice in invoice_list)

        # Step 2: Group invoice by customer

        invoices_by_customer = {}

        for customer in unique_customers:
            invoices_by_customer[customer] = list(filter(lambda inv: inv['invoice_partner_display_name'] == customer, invoice_list))

        # Step 3: Separate invoices of each customer by age range and sum Amount Due

        age_ranges = [(0, 30), (30, 60), (60, 90), (90, 120), (120, float('inf'))]
        total_amount_by_range = {}
        for customer, invoices in invoices_by_customer.items():
            customer_data = {}
            total_customer_amount = 0
            for start, end in age_ranges:
                filtered_invoices = [inv for inv in invoices if start <= inv['age'] < end]
                total_amount = sum(inv['amount_residual_signed'] for inv in filtered_invoices)
                customer_data[f'{start}-{end}'] = total_amount
                total_customer_amount += total_amount
                total_amount_by_range.setdefault(f'{start}-{end}', 0)
                total_amount_by_range[f'{start}-{end}'] += total_amount
            customer_data['Total'] = total_customer_amount
            data[customer] = customer_data

        data["Total Amount by range"] = total_amount_by_range
        data["Total Amount by range"]["Total"] = sum(list(total_amount_by_range.values()))
        data["Aging Date"] = self.aging_date.strftime("%m/%d/%Y")
        data["Company Name"] = self.env.company.name        

        return self.env.ref('accounting_customer_aging.report_customer_aging_xlsx').report_action(self, data=data)