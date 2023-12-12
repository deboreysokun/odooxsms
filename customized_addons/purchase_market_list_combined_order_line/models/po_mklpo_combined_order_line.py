from odoo import models, fields, api, _
from odoo import tools


class MarketListPurchaseOrderLineCustom(models.Model):
    _inherit = "kr.purchase.order.line"

    def _default_sub_total_usd(self):
        for line in self:
            if line.currency_id.name == "KHR":
                line.sub_total_usd = line.sub_total / 4000
            else:
                line.sub_total_usd = line.sub_total

    sub_total_usd = fields.Float('Sub total USD', store=True, default=_default_sub_total_usd,
                                 compute="_compute_sub_total_usd")

    @api.depends("sub_total", "currency_id")
    def _compute_sub_total_usd(self):
        for line in self:
            if line.currency_id.name == "KHR":
                line.sub_total_usd = line.sub_total / 4000
            else:
                line.sub_total_usd = line.sub_total


class PurchaseMarketListOrderCombinedView(models.Model):
    _name = "po.mklpo.combined.order.line"
    _auto = False
    _description = "Purchase and Market List Combined Order Line View"

    name = fields.Char('Order Reference', index=True)
    date_order = fields.Date(string='Order Date')
    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='Unit')
    price_unit = fields.Float(string='Unit Price', default=1)
    sub_total = fields.Float(string='Subtotal')
    analytic_acc = fields.Many2one('account.analytic.account', string='Analytic Account')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('progress', 'Progress'),
        ('purchase', 'Purchase Order'),
        ('validate', 'Validated'),
        ('cancel', 'Cancelled'),
        ('done', 'Locked/Done')
    ], string='Status')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'po_mklpo_combined_order_line')
        self._cr.execute("""
            CREATE OR REPLACE VIEW po_mklpo_combined_order_line AS (
                SELECT
                    row_number() OVER () AS id,
                    line.name,
                    line.date_order,
                    line.product_id,
                    line.product_qty,
                    line.product_uom,
                    line.price_unit,
                    line.sub_total,
                    line.analytic_acc,
                    line.state
                FROM
                    (
                        SELECT
                            po.name,
                            po.date_order,
                            pol.product_id,
                            pol.product_qty,
                            pol.product_uom,
                            pol.price_unit,
                            pol.price_subtotal as sub_total,
                            pol.account_analytic_id as analytic_acc,
                            po.state
                        FROM
                            purchase_order_line pol
                        LEFT JOIN
                            purchase_order po ON (po.id = pol.order_id)
        
                        UNION ALL
        
                        SELECT
                            kpo.name,
                            kpo.date_order,
                            kpol.product_id,
                            kpol.product_qty,
                            kpol.product_uom_id as product_uom,
                            kpol.price_per_unit as price_unit,
                            kpol.sub_total_usd as sub_total,
                            kpol.analytic_acc,
                            kpo.state
                        FROM
                            kr_purchase_order_line kpol
                        LEFT JOIN
                            kr_purchase_order kpo ON (kpo.id = kpol.order_id)
                    ) line
            
            )""")
