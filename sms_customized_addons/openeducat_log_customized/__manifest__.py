# -*- coding: utf-8 -*-
{
    'name': "openeducat_log_customized",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Chnadara Lee",

    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'openeducat_core',
                'openeducat_attendance',
                ],

    # always loaded
    'data': [
        'data/paper_format.xml',
        'report/log_record_report_pdf.xml',  
        'views/log_record_view.xml',
        'report/report_name.xml',
        'wizard/log_record.xml',
        'menu/log_record_menu.xml', 
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
