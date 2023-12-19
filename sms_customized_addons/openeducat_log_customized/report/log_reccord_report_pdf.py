import calendar
import time
from datetime import datetime
from odoo import models, api, _, fields, tools


class ReportLogRecordGenerate(models.AbstractModel):
    _name = "report.openeducat_log_customized.log_report"
    _description = "Log Record Report"



    def _get_body_data(self, data=None):
        record_log_query = '''SELECT op_attendance_sheet.attendance_date, 
                                        op_timing.name,
                                        op_attendance_sheet.log_record
                                            FROM op_session 
                                                        INNER JOIN op_attendance_sheet 
                                                        ON op_session.id = op_attendance_sheet.session_id
                                                        INNER JOIN op_timing
                                                        ON op_session.timing_id = op_timing.id
                                                            where  op_attendance_sheet.course_id = %s
                                                                AND op_attendance_sheet.batch_id = %s
                                                                AND op_session.faculty_id = %s
                                                                AND op_session.subject_id = %s
                                                                AND op_attendance_sheet.attendance_date >= %s
                                                                AND op_attendance_sheet.attendance_date <= %s
                                                        ORDER BY 
                                                            op_attendance_sheet.attendance_date ASC,
                                                            op_timing.name ASC'''
                                                
        self.env.cr.execute(record_log_query,(data['course_id'][0], data['batch_id'][0], data['faculty_id'][0], data['subject_id'][0], data['start_date'], data['end_date']))
        log_record = self.env.cr.dictfetchall()

        return log_record

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        course = self.env['op.course'].search([('id', '=', data['course_id'][0])])
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'data': data,
            'semester': course.name,
            'department': course.department_id.name,
            'body_data': self._get_body_data(data)
        }
        return docargs