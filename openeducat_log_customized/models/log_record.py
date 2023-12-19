from odoo import models, fields, _
from odoo.exceptions import UserError

class OpLogRecord(models.Model):
    _inherit = "op.attendance.sheet"

    log_record = fields.Text('Log Record', size = 256)

