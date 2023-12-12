from odoo import models, fields, api, _
from odoo import tools


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Create a related field to fetch related purchase history records
    history_ids = fields.One2many(
        'product.template.purchase.history',
        'product_history_id',
        string='Purchase History'
    )


class ProductTemplatePurchaseHistoryCustom(models.Model):
    _name = "product.template.purchase.history"
    _description = "Purchase history for product template"

    product_id = fields.Many2one('product.product',
                                 'Product',
                                 tracking=True)
    product_history_id = fields.Many2one('product.template', 'Product Template')
    price_per_unit_est = fields.Float('Estimated Price')
    product_uom_id = fields.Many2one('uom.uom', 'Unit')
    product_qty = fields.Float('Quantity', tracking=True, digits='Product Unit of Measure')
    currency_id = fields.Many2one('res.currency', "Currency", required=True, domain=[('name', 'in', ('USD', 'KHR'))])
    date_order = fields.Date('Order Date', required=True)
    supplier_id = fields.Many2one('kirirom.supplier', 'Kirirom Supplier')
