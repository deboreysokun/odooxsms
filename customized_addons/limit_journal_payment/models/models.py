from odoo import fields, models


class UsersJournalLimit(models.Model):
    _inherit = 'res.users'

    journal_limit_access = fields.Boolean("Journal Limit Access")
    journal_ids = fields.Many2many('account.journal', string='Journal')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _compute_journal_domain_and_types(self):
        res = super(AccountPayment, self)._compute_journal_domain_and_types()
        if self.env.user.journal_limit_access:
            journal_ids = tuple([journal.id for journal in self.env.user.journal_ids])
            res['domain'].append(('id', 'in', journal_ids))
        return res
