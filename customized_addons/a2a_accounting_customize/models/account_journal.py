from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_salary_journal = fields.Boolean("Is Salary Journal")


class AccountMoveIsSalaryJournal(models.Model):
    _inherit = "account.move"

    is_salary_journal = fields.Boolean(readonly=True, related='journal_id.is_salary_journal')
