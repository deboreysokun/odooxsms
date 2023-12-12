# -*- coding: utf-8 -*-
{
    'name': "Accounting Customer Aging",

    'summary': """
        Accounting Customer Aging for Odoo Upgrade 4.0 """,

    'author': "Thy Saonan(B8), Pich Rachana(B8), Hin Chanritheavuth(B9)",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '13.3.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'odoo_report_xlsx'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/customer_aging_view.xml',
        'wizard/customer_aging_wizard_view.xml',
        'views/vendor_aging_view.xml',
        'wizard/vendor_aging_wizard_view.xml',
        'report/report.xml',
    ],
    "installable": True,
    "application": False,
}
