from odoo import fields, models


class AccountFinancialReportCustomize(models.Model):
    _inherit = "account.financial.report"
    show_parent = fields.Boolean('Show Parent')


class CashFlowLogic(models.Model):
    _inherit = "account.account"
    cashflow_logic = fields.Selection([
        ('new_old', 'Current - Previous'),
        ('old_new', 'Previous - Current'),
    ], string="Cashflow Logic")


class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"

    beginning_balance = fields.Many2many("account.move", string="Beginning Balance")
