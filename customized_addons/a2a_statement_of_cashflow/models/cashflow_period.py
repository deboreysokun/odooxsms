from odoo import models, fields


class CashflowPeroid(models.Model):
    _name = "cashflow.period"
    _inherit = "accounting.report"
    _rec_name = "name"

    name = fields.Char(string="Cashflow Period", require=True)