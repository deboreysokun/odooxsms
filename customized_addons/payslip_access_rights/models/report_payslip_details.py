from odoo import api, models


class PayslipDetailsReport(models.AbstractModel):
    _inherit = 'report.om_hr_payroll.report_payslip_details'

    @api.model
    def _get_report_values(self, docids, data=None):
        payslips = self.env['hr.payslip'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'get_details_by_rule_category': self.sudo().get_details_by_rule_category(payslips.mapped('details_by_salary_rule_category').filtered(lambda r: r.appears_on_payslip)),
            'get_lines_by_contribution_register': self.sudo().get_lines_by_contribution_register(payslips.mapped('line_ids').filtered(lambda r: r.appears_on_payslip)),
        }