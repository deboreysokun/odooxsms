# -*- coding: utf-8 -*-
{
    'name': "inventory_customize_new_fields",
    'version': "13.3.1",
    'author': "Ven Channa (B8)",
    'category': 'Inventory',
    'website': "https://docs.google.com/document/d/1BnkagxY98jsIN8xWbyAzUvFCWg8yi084c95d730ImtA/edit?usp=sharing",
    'summary': "Customize some fields and add new features",
    'depends': ['base', 'stock', 'sale', 'account', 'market_list_odoo13', 'product', 'barcodes', 'inventory_fields_customize', 'point_of_sale', 'pos_product_available', 'mrp'],
    'data': [
        'views/view_access_right_customized.xml',
        'views/market_list_history_view.xml',
        'views/stock_inventory_adjustment.xml',
        'wizards/stock_transfer_details.xml',
    ],
}
