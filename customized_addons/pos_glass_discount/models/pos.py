# -*- coding: utf-8 -*-

from odoo import models, fields


class POSConfig(models.Model):
    _inherit = "pos.config"
    show_glass_discount = fields.Boolean("Show Glass Discount")


class POSOrderLine(models.Model):
    _inherit = "pos.order.line"
    glass_discount = fields.Integer("Glass Disc")
