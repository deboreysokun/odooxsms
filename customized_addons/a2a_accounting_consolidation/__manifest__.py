# -*- coding: utf-8 -*-
{
    'name': "A2A Accounting Consolidation",

    'summary': """
        Accounting Consolidation for Odoo Upgrade 3.0 """,

    'author': "Thy Saonan(B8), Pich Rachana(B8), Reth Sokmeta(B8)",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '13.3.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'a2a_statement_of_cashflow'],

    # always loaded
    'data': [
        'security/account_security.xml',
        'views/exchange_rate_date.xml',
        'views/to_eliminate_field.xml',
        'views/consolidation_menuitem.xml',
        'views/res_partner.xml',
        'wizards/accounting_consolidation.xml',
    ],
}
