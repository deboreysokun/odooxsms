from odoo import fields, models

class CustomerAging(models.Model):
    _inherit = "account.move"
    
    age = fields.Integer(string="Age")