from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_consolidation_user = fields.Boolean(string="Consolidation User")

    def can_do_elimination(self):
        contacts = [self.env.company.partner_id.id]
        for company in self.env.company.child_ids:
            contacts.append(company.partner_id.id)
        return self.id in contacts or self.is_consolidation_user
