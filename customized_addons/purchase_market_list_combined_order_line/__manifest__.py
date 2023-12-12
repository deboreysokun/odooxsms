# -*- coding: utf-8 -*-
{
    'name': "Purchase Market List Combined Order Line",
    'description': """
        This addon is used to combine all order lines from Purchase application and Market List application as a summary.
    """,

    'author': "DaraPichchan Huy(B8)",
    'version': '13.2.1',

    'depends': ['base', 'purchase', 'market_list_odoo13'],

    'data': [
        'security/ir.model.access.csv',
        'views/purchase_marketlist_order_combined_view.xml'
    ],

    'installable': True,
    'auto_install': False
}
