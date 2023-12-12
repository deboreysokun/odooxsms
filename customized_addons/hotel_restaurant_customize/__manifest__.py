{
    "name": "Hotel Restaurant Customize",
    "version": "13.2.1",
    "author": "Yong Vuthivann (B8), Ven Channa (B8)",
    "category": 'Hotel',
    "website": "https://docs.google.com/document/d/1O3dE5Z93qx9kn60kKuHGCJSWxeZ63Myg/edit",
    "summary": """
        Customize on 
    """,
    'depends': ['base', 'hotel', 'hotel_restaurant', 'point_of_sale', 'product', 'activity', 'stock', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/restaurant_customize.xml',
        'views/restaurant_in_folio.xml',
        'report/report_kitchen_order_ticket_template.xml',
        'report/report_customer_bill_template.xml',
        'report/report.xml',
        # 'views/sequence_restaurant.xml',
    ],
}
