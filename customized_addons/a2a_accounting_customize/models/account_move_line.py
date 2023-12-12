from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    debit_tax_inc = fields.Monetary(string='Debit Tax', compute='_compute_debit_tax', store=True, group_operator='sum')

    @api.depends('debit', 'tax_ids.amount')
    def _compute_debit_tax(self):
        for line in self:
            if line.tax_ids:
                line.debit_tax_inc = (1 + (line.tax_ids.amount / 100)) * (line.debit)
            else:
                line.debit_tax_inc = line.debit

