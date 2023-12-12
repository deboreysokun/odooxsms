# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrEmployee(models.Model):
     _inherit = 'hr.employee'
     
     payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslips', groups="hr_payroll.group_hr_payroll_user,base.group_user")
     
     user_id = fields.Many2one('res.users', string='User', groups="hr_payroll.group_hr_payroll_user,base.group_user")