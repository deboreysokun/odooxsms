from odoo import models, fields, api


class MarketListLocation(models.Model):
    _description = 'This model is used to create location to choose in Purchase Order'
    _name = "market.list.location"

    name = fields.Char('Locations', size=256, tracking=True, required=True)

    vkr_operation_type = fields.Many2one('stock.picking.type', 'vKirirom Operation Type', tracking=True)
    a2a_operation_type = fields.Many2one('stock.picking.type', 'A2A Operation Type', tracking=True)
    source_location = fields.Many2one('stock.location', 'Source', tracking=True)
    vkr_destination = fields.Many2one('stock.location', 'vKirirom Destination', tracking=True)
    a2a_destination = fields.Many2one('stock.location', 'A2A Destination', tracking=True)
    sequences = fields.Many2many('ir.sequence', string='Sequences', index=True, required=True)
    company = fields.Many2one('res.company', 'Company', tracking=True)
    isDefault = fields.Boolean('IsDefault')
