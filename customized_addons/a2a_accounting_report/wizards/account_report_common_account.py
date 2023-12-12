from odoo import models
from odoo.tools.misc import get_lang


class AccountCommonAccountExcelReport(models.TransientModel):
  _inherit = 'account.common.report'

  def check_report_xlsx(self):
    self.ensure_one()
    data = {}
    data['ids'] = self.env.context.get('active_ids', [])
    data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
    data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
    used_context = self._build_contexts(data)
    data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
    return self.with_context(discard_logo_check=True)._print_report_xlsx(data)
