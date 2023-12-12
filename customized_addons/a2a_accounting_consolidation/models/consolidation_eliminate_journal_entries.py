from odoo import models, fields

class ToEliminateJournalEntry(models.Model):
    _inherit = 'account.move'

    to_eliminate = fields.Boolean(string='To Eliminate')
