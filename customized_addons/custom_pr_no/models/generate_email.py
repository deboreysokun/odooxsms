from odoo import _, models, fields, api, tools


class MailTemplateInherit(models.Model):
    _inherit = "mail.template"

    def generate_recipients(self, results, res_ids):
        """Generates the recipients of the template. Default values can ben generated
        instead of the template values if requested by template or context.
        Emails (email_to, email_cc) can be transformed into partners if requested
        in the context. """
        self.ensure_one()

        if self.use_default_to or self._context.get('tpl_force_default_to'):
            records = self.env[self.model].browse(res_ids).sudo()
            default_recipients = self.env['mail.thread']._message_get_default_recipients_on_records(records)
            for res_id, recipients in default_recipients.items():
                results[res_id].pop('partner_to', None)
                results[res_id].update(recipients)

        records_company = None
        if self._context.get('tpl_partners_only') and self.model and results and 'company_id' in self.env[self.model]._fields:
            records = self.env[self.model].browse(results.keys()).read(['company_id'])
            records_company = {rec['id']: (rec['company_id'][0] if rec['company_id'] else None) for rec in records}

        for res_id, values in results.items():
            partner_ids = values.get('partner_ids', list())
            if self._context.get('tpl_partners_only'):
                mails = tools.email_split(values.pop('email_to', '')) + tools.email_split(values.pop('email_cc', ''))
                Partner = self.env['res.partner']
                User = self.env['res.users']
                if records_company:
                    Partner = Partner.with_context(default_company_id=records_company[res_id])
                    User = User.with_context(default_company_id=records_company[res_id])
                for mail in mails:
                    partner_id = Partner.find_or_create(mail)
                    approver = User.find_or_create(mail)
                    partner_ids.append(partner_id)
                    user = User.search([('partner_id', '=', approver)], limit=1)
                    if user:
                        partner_ids.append(user.partner_id.id)
            partner_ids = values.get('partner_ids', [])
            partner_to = values.pop('partner_to', '')
            if partner_to:
                tpl_partner_ids = []
                # users_to_fetch = []
                for pid in partner_to.split(','):
                    pid = pid.strip()
                    if pid.isdigit():
                        tpl_partner_ids.append(int(pid))
                    else:
                        partner_ids += self.env['res.partner'].sudo().search([('name', '=', pid)]).ids
                        user_ids = self.env['res.users'].sudo().search([('login', '=', pid)])
                        partner_ids += user_ids.mapped('partner_id').ids
                partner_ids += self.env['res.partner'].sudo().browse(tpl_partner_ids).exists().ids
                user_ids = self.env['res.users'].sudo().search([('id', 'in', tpl_partner_ids)])
                if user_ids:
                    partner_ids = user_ids.mapped('partner_id').ids
            results[res_id]['partner_ids'] = partner_ids
        return results


class PurchaseOrderGenerateEmail(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'mail.thread', 'mail.activity.mixin', 'portal.mixin']

    def send_email_to_approver(self):
        self.ensure_one()
        template_id = self.env.ref('custom_pr_no.send_email_template_purchase_order_approval').id
        ir_model_data = self.env['ir.model.data']
        compose_form_id = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='purchase.order',
            active_model='purchase.order',
            active_id=self.ids[0],
            default_res_id=self.ids[0],
            default_use_template=bool(template_id),
            default_template_id=template_id,
            default_composition_mode='comment',
            custom_layout="mail.mail_notification_paynow",
            force_email=True,
            mark_rfq_as_sent=True,
        )

        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id.id, 'form')],
            'view_id': compose_form_id.id,
            'target': 'new',
            'context': ctx,
        }




class PurchaseRequestGenerateEmail(models.Model):
    _name = 'purchase.request'
    _inherit = ['purchase.request', 'portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    _STATES = [
        ("draft", "Draft"),
        ("to_approve", "To be approved"),
        ("sent", "Email Sent"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("done", "Done"),
    ]

    user_id = fields.Many2one(
        'res.users', string='Request Representative', index=True, tracking=True,
        default=lambda self: self.env.user, check_company=True)

    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        track_visibility="onchange",
        required=True,
        copy=False,
        default="draft",
    )

    def _compute_access_url(self):
        super(PurchaseRequestGenerateEmail, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/request/%s' % (order.id)

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_request_as_sent'):
            self.filtered(lambda o: o.state == 'draft').write({'state': 'to_approve'})
        return super(PurchaseRequestGenerateEmail, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

    def send_pr_email_to_approver(self):
        self.write({'state': "sent"})
        self.ensure_one()
        template_id = self.env.ref('custom_pr_no.send_email_template_purchase_request_approver').id
        print('compose form---')
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        print('composed')
        ctx = dict(
            default_model='purchase.request',
            default_res_id= self.ids[0],
            default_use_template=bool(template_id),
            default_template_id=template_id,
            default_composition_mode='comment',
            custom_layout="mail.mail_notification_paynow",
            force_email=True,
            mark_request_as_sent=True,
        )

        if self.state in ['to_approve']:
            ctx['model_description'] = _('Request for Approval')
        else:
            ctx['model_description'] = _('Approved')
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }