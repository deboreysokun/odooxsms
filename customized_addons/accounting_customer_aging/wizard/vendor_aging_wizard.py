from odoo import fields, api, models
import xlwt

class VendorAgingWizard(models.TransientModel):
    _name = "account.move.vendor.aging.wizard"
    
    aging_date = fields.Date(string='Aging Date')
    def action_compute_vendor_aging(self):
        domain = [('type', '=', 'in_invoice'), ('state', '=', 'posted'), ('invoice_payment_state', '!=', 'paid')]
        invoices = self.env['account.move'].search(domain)
        for invoice in invoices:
            age = (self.aging_date - invoice.invoice_date_due).days if self.aging_date > invoice.invoice_date_due else 0
            invoice.age = age

        return {
        'name': 'vendor Aging',
        'view_mode': 'tree,form',
        'views': [
            (self.env.ref('accounting_customer_aging.vendor_aging_list_view').id, 'tree'),
            (self.env.ref('account.view_move_form').id, 'form'),
        ],
        'res_model': 'account.move',
        'domain': domain,
        'type': 'ir.actions.act_window',
        'target': 'current',
    }

    def action_print_excel_report(self):

        data = {}

        domain = [('type', '=', 'in_invoice'), ('state', '=', 'posted'), ('invoice_payment_state', '!=', 'paid')]

        invoice_list = self.env['account.move'].search(domain)
        for invoice in invoice_list:
            invoice.age = (self.aging_date - invoice.invoice_date_due).days if self.aging_date > invoice.invoice_date_due else 0
        
        # Step 1: Get Unique Sets of vendor

        unique_vendors = set(invoice['invoice_partner_display_name'] for invoice in invoice_list)

        # Step 2: Group invoice by vendor

        invoices_by_vendor = {}

        for vendor in unique_vendors:
            invoices_by_vendor[vendor] = list(filter(lambda inv: inv['invoice_partner_display_name'] == vendor, invoice_list))

        # Step 3: Separate invoices of each vendor by age range and sum Amount Due

        age_ranges = [(0, 30), (30, 60), (60, 90), (90, 120), (120, float('inf'))]

        total_amount_by_range = {}
        for vendor, invoices in invoices_by_vendor.items():
            vendor_data = {}
            total_vendor_amount = 0
            for start, end in age_ranges:
                filtered_invoices = [inv for inv in invoices if start <= inv['age'] < end]
                total_amount = sum(inv['amount_residual_signed'] for inv in filtered_invoices)
                vendor_data[f'{start}-{end}'] = total_amount
                total_vendor_amount += total_amount
                total_amount_by_range.setdefault(f'{start}-{end}', 0)
                total_amount_by_range[f'{start}-{end}'] += total_amount
            vendor_data['Total'] = total_vendor_amount
            data[vendor] = vendor_data

        data["Total Amount by range"] = total_amount_by_range
        data["Total Amount by range"]["Total"] = sum(list(total_amount_by_range.values()))
        data["Aging Date"] = self.aging_date.strftime("%m/%d/%Y")
        data["Company Name"] = self.env.company.name  

        return self.env.ref('accounting_customer_aging.report_vendor_aging_xlsx').report_action(self, data=data)