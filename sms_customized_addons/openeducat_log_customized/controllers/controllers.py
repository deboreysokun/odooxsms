# -*- coding: utf-8 -*-
# from odoo import http


# class OpeneducatLogRecordCustomized(http.Controller):
#     @http.route('/openeducat_log_customized/openeducat_log_customized/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/openeducat_log_customized/openeducat_log_customized/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('openeducat_log_customized.listing', {
#             'root': '/openeducat_log_customized/openeducat_log_customized',
#             'objects': http.request.env['openeducat_log_customized.openeducat_log_customized'].search([]),
#         })

#     @http.route('/openeducat_log_customized/openeducat_log_customized/objects/<model("openeducat_log_customized.openeducat_log_customized"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('openeducat_log_customized.object', {
#             'object': obj
#         })
