# -*- coding: utf-8 -*-
{
    'name': "Product Template Purchase History",
    'description': """
        Display each product's history in notebook view.
    """,

    'author': "DaraPichchan Huy(B8)",
    'version': '13.2.1',

    'depends': ['base', 'purchase', 'market_list_odoo13'],

    'data': [
        'security/ir.model.access.csv',
        'views/product_template_purchase_history.xml'
    ],

    'installable': True,
    'auto_install': False
}
