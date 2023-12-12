from odoo import models, api, fields


class VendorBillCustomize(models.Model):
  _inherit = 'account.move'
  vendor_bill_no = fields.Char(string="Vendor Bill Number", readonly=True, states={'draft': [('readonly', False)]}, )
  account = property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
                                                          string="Account Payable",
                                                          related="partner_id.property_account_payable_id",
                                                          tracking=True
                                                          )
  invoice_origin = fields.Char(string='Origin', readonly=True, tracking=True, states={'draft': [('readonly', False)]},
                               help="The document(s) that generated the invoice.")

  purchaser = fields.Many2one('res.users', copy=False, tracking=True, string='Purchaser',
                              domain=[('groups_id.category_id.name', '=', 'Purchase')])

  def write(self, vals):
    for move in self:
      if move.name != '/' and 'journal_id' in vals:
        if move.journal_id.id != vals['journal_id']:
          move.name = '/'
    return super(VendorBillCustomize, self).write(vals)

  prev_journal = fields.Many2one('account.journal', string='Previous Journal', readonly=True)

  def post(self):
    for move in self:
      if not move.prev_journal.name:
        move.prev_journal = move.journal_id
      if move.journal_id == move.prev_journal:
        return super().post()
      move.prev_journal = move.journal_id
      if move.name != '/':
        move.name = '/'
    return super().post()


class RegisterPayment(models.Model):
  _inherit = 'account.payment'

  memo_payment = fields.Char(string='Memo', readonly=True, states={'draft': [('readonly', False)]})

  def post(self):
    return_val = super().post()
    for rec in self:
      if rec.payment_difference_handling == 'reconcile':
        journal_item = self.env['account.move.line'].search([('payment_id', '=', rec.id),
                                                             ('name', '=', rec.writeoff_label)])
        payment_diff = journal_item.credit - journal_item.debit
        self.env['account.analytic.line'].create(
          [{
            'name': journal_item.name,
            'partner_id': journal_item.partner_id.id,
            'date': journal_item.move_id.date,
            'move_id': journal_item.id,
            'unit_amount': journal_item.quantity,
            'general_account_id': journal_item.account_id.id,
            'amount': payment_diff,
            'account_id': rec.analytic_id.id,
            'ref': rec.payment_ref,
            'company_id': rec.company_id.id,
          }]
        )
    return return_val

  @api.model
  def default_get(self, default_fields):
    rec = super(RegisterPayment, self).default_get(default_fields)
    active_ids = self._context.get('active_ids') or self._context.get('active_id')
    active_model = self._context.get('active_model')

    if not active_ids or active_model != 'account.move':
      return rec

    invoices = self.env['account.move'].browse(active_ids).filtered(lambda move: move.is_invoice(include_receipts=True))
    rec.update({
      'communication': invoices[0].name,
      'memo_payment': invoices[0].invoice_payment_ref or invoices[0].ref or invoices[0].name,
    })

    return rec

  def _prepare_payment_moves(self):
    res = super(RegisterPayment, self)._prepare_payment_moves()
    for index, payment in enumerate(self, 0):
      if payment.memo_payment:
        res[index]['invoice_payment_ref'] = payment.memo_payment

    return res
