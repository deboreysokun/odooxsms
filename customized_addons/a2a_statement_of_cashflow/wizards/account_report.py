from odoo import fields, models, api


class AccountReportCashflow(models.TransientModel):
    _inherit = "accounting.report"
    cashflow_period = fields.Many2one('cashflow.period', string="Cashflow Period")

    @api.onchange('cashflow_period')
    def _onchange_cashflow_period(self):
        for acc_report in self:
            if not self.cashflow_period:
                return
            cashflow_period = acc_report.cashflow_period
            acc_report.target_move = cashflow_period.target_move
            acc_report.date_to = cashflow_period.date_to
            acc_report.date_from = cashflow_period.date_from
            acc_report.date_to_cmp = cashflow_period.date_to_cmp
            acc_report.date_from_cmp = cashflow_period.date_from_cmp
            acc_report.company_id = cashflow_period.company_id
            acc_report.account_report_id = cashflow_period.account_report_id
            acc_report.enable_filter = cashflow_period.enable_filter
            acc_report.label_filter = cashflow_period.label_filter
