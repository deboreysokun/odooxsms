# -*- coding: utf-8 -*-
{
    'name': "Limit Journal Payment",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Thy Saonan",
    'website': "",
    'category': 'Accouting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'views/views.xml',
    ],
}
