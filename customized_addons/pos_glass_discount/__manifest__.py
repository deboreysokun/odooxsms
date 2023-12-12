# -*- coding: utf-8 -*-
{
    'name': "POS Glass Discount",
    'description': """
        The Purpose of this module is to allow discount on drink in Pine View Restaurant
    """,
    'author': "Thy Saonan (B8)",
    'category': 'POS',
    'depends': ['base', 'point_of_sale'],
    'qweb': ['static/src/xml/pos.xml'],
    # always loaded
    'data': [
        'views/pos_order_line.xml',
        'views/pos_config.xml',
        'views/pos_glass_discount.xml'
    ],
}
