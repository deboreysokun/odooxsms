from odoo import _, models, fields, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools import datetime
import datetime


class PurchaseOrderInheritCustom(models.Model):
    _inherit = 'purchase.order'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    new_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        track_visibility="onchange",
        required=True,
        states=READONLY_STATES,

    )

# add new analytic account inside RFQ form and put it onchange the acc line
    @api.onchange('new_analytic_account_id', 'account_analytic_id')
    def _onchange_analytic_account_id(self):
        for order in self:
            analytic_id = order.new_analytic_account_id
            for line in order.order_line:
                line.update(
                    {
                        "account_analytic_id": analytic_id,
                    }
                )

    @api.model
    def create(self, vals):
        company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
        if vals.get('name', 'New') == 'New':
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            vals['name'] = self.env['ir.sequence'].with_context(force_company=company_id).next_by_code('purchase.order',
                                                                                                       sequence_date=seq_date) or '/'
            order = super(PurchaseOrderInheritCustom, self.with_context(company_id=company_id)).create(vals)
            order._onchange_analytic_account_id()
        return order

    def write(self, vals):
        res = super(PurchaseOrderInheritCustom, self).write(vals)
        self._onchange_analytic_account_id()
        if vals.get('date_planned'):
            self.order_line.filtered(lambda line: not line.display_type).date_planned = vals['date_planned']
        return res


class PurchaseOrderAnalyticLine(models.Model):
    _inherit = 'purchase.order.line'

    account_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        # readonly=True,
    )




