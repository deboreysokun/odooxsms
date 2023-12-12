from odoo import fields, models, api


class ExchangeRateLine(models.TransientModel):
    _name = "exchange.rate"

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    exchange_rate = fields.Integer(string="Exchange Rate")
    report_id = fields.Many2one('accounting.report')


class ConsolidationExchangeRate(models.TransientModel):
    _inherit = "accounting.report"
    company_exchange_rates = fields.One2many('exchange.rate', 'report_id', string="Company Exchange Rates")

    @api.model
    def default_get(self, fields_list):
        res = super(ConsolidationExchangeRate, self).default_get(fields_list)
        company_id = self._context.get("allowed_company_ids")[0]
        company = self.env['res.company'].browse(company_id)
        child_ids = []
        for child in company.child_ids:
            if company.currency_id != child.currency_id:
                child_ids.append((0, 0, {'company_id': child.id, 'currency_id': child.currency_id.id}))
        res.update({'company_exchange_rates': child_ids})
        return res
