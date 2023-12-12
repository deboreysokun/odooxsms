# -*- coding: utf-8 -*-
{
    'name': "A2A Statement Of Cashflow",

    'summary': """
        Cash flow customization for Odoo Upgrade 3.0
    """,
    'author': "Thy Saonan(B8), Pich Rachana(B8)",
    'website': "...",
    'category': 'Accounting',
    'version': '13.3.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'a2a_accounting_report'],

    # always loaded
    'data': [
        'views/accounting_financial_report.xml',
        'views/account_reports_settings.xml',
        'reports/report_accounting_financial_report.xml',
        'wizards/accounting_statement_of_cashflows.xml',

    ],

}
