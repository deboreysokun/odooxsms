# -*- coding: utf-8 -*-
{
  'name': "Employee Payslip Access",
  'summary': """Add access rights to employees to access their payslips.""",
  'author': "Reth Sokmeta(B8), Sambath Vatana(B8)",
  'description': """
            -Add access rights payslip to employee.
            -Remove group 'Payroll Officer' from 'Employee Payslips' menu item.
            -If you installed this module and want to uninstall it you should add group 'Payroll Officer' to 'Employee Payslips' [menu item] manually. """,
  'depends': ['base', 'om_hr_payroll', 'hr'],
  'installable': True,
  'auto_install': False,
  'data': [
    'security/ir_rule.xml',
    'security/access_info.xml',
    'views/payroll_view.xml',
    'views/report_payslip_templates.xml',
    'views/restrict_employee_view.xml',
    'security/ir.model.access.csv'
  ],
  'images': ["static/description/image.png"],
}
