from odoo import fields, models, api

class ExchangeRateDate(models.Model):
    _inherit = "res.currency.rate"


    name = fields.Date(string='Date From', required=True, index=True,
                           default=lambda self: fields.Date.today())
    date_to = fields.Date(string='Date To', required=True, index=True,
                           default=lambda self: fields.Date.today())

