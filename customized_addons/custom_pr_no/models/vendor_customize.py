from odoo import fields, api, models


class VendorCustomize(models.Model):
  _inherit = 'res.partner'

  internal_ref = fields.Char(string='Internal Reference', index=True, copy=False)
  internal_ref_customer = fields.Char(string='Internal Reference', index=True, copy=False)

  _sql_constraints = [
    ('internal_ref_uniq', 'unique(internal_ref)', "This reference code is already exist!"),
    ('internal_ref_customer_uniq', 'unique(internal_ref_customer)', "This reference code is already exist!")
  ]


  @api.depends("firstname", "lastname", 'eng_name', 'khmer_name', 'internal_ref', 'internal_ref_customer')
  def _compute_name(self):
    """Write the 'name' field according to splitted data."""
    for record in self:
      if not record.is_company:
        record.name = str(record.internal_ref_customer or '') + str(record.internal_ref or '') + " " + str(
          record.khmer_name or '') + " " + record._get_computed_name(record.lastname, record.firstname)
      else:
        record.firstname = record.eng_name or record.khmer_name or record.internal_ref or record.internal_ref_customer
        record.name = str(record.internal_ref_customer or '') + str(record.internal_ref or '') + " " + str(record.khmer_name or '') + " " + str(
          record.eng_name or '')


  @api.model
  def _default_receivable_account(self):
    type_obj = self.env["account.account"]
    company_id = self.env.context.get("company_id") or self.env.company.id
    receivable = type_obj.search(
      [("code", "=", "130001"), ("company_id", "=", company_id),
       ("name", "like", "%Account Receivable")]
    )
    return receivable

  @api.model
  def _default_payable_account(self):
    type_obj = self.env["account.account"]
    company_id = self.env.context.get("company_id") or self.env.company.id
    payable = type_obj.search(
      [("code", "=", "200001"), ("company_id", "=", company_id),
       ("name", "like", "%Accounts Payable")]
    )
    return payable


  property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
                                                   string="Account Receivable",
                                                   domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
                                                   default=_default_receivable_account,
                                                   help="This account will be used instead of the default one as the receivable account for the current partner",
                                                   required=True)
  property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
                                                string="Account Payable",
                                                default=_default_payable_account,
                                                domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
                                                help="This account will be used instead of the default one as the payable account for the current partner",
                                                required=True)