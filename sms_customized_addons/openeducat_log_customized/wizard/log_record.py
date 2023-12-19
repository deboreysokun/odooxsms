
from datetime import datetime
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class LogRecord(models.TransientModel):
    _name = "log.record.report"
    _description = "create log record wizard"

    faculty_id = fields.Many2one('op.faculty', 'Faculty', required=True)
    head_dep_id = fields.Many2one('hr.employee', 'Confirmed by', required=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True)
    course_id = fields.Many2one('op.course', 'Course', required=True)
    batch_id = fields.Many2one('op.batch', 'Group', domain="[('course_id', '=', course_id)]", required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)

    
    @api.onchange('batch_id', 'course_id', 'faculty_id')
    def _onchange_date(self):
        _res={}
        if self.batch_id and self.course_id:
            if self.batch_id.course_id != self.course_id:
                self.batch_id = False/openeducat_student_leave_request/models

            fac_list = []
            fac_subject = self.env['op.session'].search([('course_id', '=' ,self.course_id.id),('batch_id', '=' ,self.batch_id.id)]).faculty_id
            for fac in fac_subject:
                fac_list.append(fac.id)
            _res['domain'] = {'faculty_id': [('id', 'in', fac_list)]}

            # if not self.faculty_id:
            #     subject_ids = self.env['op.student.course'].search([('course_id', '=' ,self.course_id.id)]).subject_ids
            #     sub_list = []
            #     for sub in subject_ids:
            #         sub_list.append(sub.id)
            #     _res['domain'] = {'subject_id': [('id', 'in', sub_list)]}

            # print('=fac====', fac_list)
            
        if self.batch_id :
            self.start_date = self.batch_id.start_date
            self.end_date = self.batch_id.end_date


        if self.faculty_id:
            session_subject = self.env['op.session'].search([('course_id', '=' ,self.course_id.id),('batch_id', '=' ,self.batch_id.id),('faculty_id', '=' ,self.faculty_id.id)]).subject_id
            subjects = []
            for subj in session_subject:
                subjects.append(subj.id)
            _res['domain'] = {'subject_id': [('id', 'in', subjects)]}

        return _res

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for time in self:
            start_date = fields.Date.from_string(time.start_date)
            end_date = fields.Date.from_string(time.end_date)
            if end_date < start_date:
                raise ValidationError(_('End Date cannot be set before Start Date.'))

            if end_date > self.batch_id.end_date:
                raise ValidationError(_('End Date is not in this semester. It should be in the term of ' 
                                            + str(self.batch_id.start_date) + ' to ' + str(self.batch_id.end_date)))
            
            if start_date < self.batch_id.start_date:
                raise ValidationError(_('Start Date is not in this semester.It should be in the term of ' 
                                            + str(self.batch_id.start_date) + ' to ' + str(self.batch_id.end_date)))
            

    def gen_log_report(self):
        template = self.env.ref(
            'openeducat_log_customized.log_report_pdf')
        data = self.read(
            ['course_id', 'faculty_id', 'batch_id', 'subject_id', 'start_date', 'head_dep_id', 'end_date'])[0]
        return template.report_action(self, data=data)





