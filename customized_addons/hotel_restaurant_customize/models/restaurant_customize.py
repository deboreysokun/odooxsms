from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import time

from odoo.tools import float_is_zero


class ProductCategoryName(models.Model):
    _inherit = "product.category"

    name = fields.Char('Name', index=True, required=False)


class RestaurantCustomize(models.Model):
    _inherit = 'hotel.restaurant.order'

    # for field o_date and button cancel invisible for normal user
    def _get_user_access_right(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('hotel.group_hotel_manager'):
            return False
        else:
            return True

    def _default_revenue_date(self):
        return self.o_date or fields.Datetime.now()

    access_right = fields.Boolean("Check Access Right", default=_get_user_access_right)
    revenue_date = fields.Datetime("Revenue Date", default=_default_revenue_date)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("order", "Order Created"),
            ("waiting", "Waiting Validate"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        "State",
        required=True,
        readonly=True,
        default="draft",
    )
    folio_id = fields.Many2one("hotel.folio", "Folio No", domain=[('state', '=', 'draft')])
    hotel_picking = fields.Many2one('stock.picking', 'Picking', tracking=True, readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    user_id = fields.Many2one(
        comodel_name='res.users', string='Responsible',
        help="Person who uses the cash register. It can be a reliever, a student or an interim employee.",
        default=lambda self: self.env.uid,
    )
    table_number_ids = fields.One2many("hotel.table.order.list", "table_order_id", "New Table List")

    @api.model
    def _get_tax_default(self):
        return 10

    tax = fields.Float("VAT (%)", default=_get_tax_default)
    date_action = fields.Datetime('Created on', required=False, readonly=False, select=True
                                  , default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), )
    last_update_date = fields.Datetime('Last Modified on', readonly=False, required=False)
    pos_ids = fields.Many2one(
        "pos.config", "Restaurant", required=True, domain=[('name', '=', ['Big Party Tent', 'Pine View Restaurant'])]
    )

    # new_order_no = fields.Char(string='Table Order', readonly=True)

    # Customized when Folio no room_no add default room in order to make order in Table Order
    @api.onchange("folio_id")
    def _onchange_folio_id(self):
        """
        When you change folio_id, based on that it will update
        the customer_id and room_number as well
        ---------------------------------------------------------
        @param self: object pointer
        """
        if self.folio_id:
            self.update(
                {
                    "customer_id": self.folio_id.partner_id.id,
                }
            )
            if self.folio_id.room_line_ids:
                self.update(
                    {
                        "room_id": self.folio_id.room_line_ids[0].product_id.id,
                    }
                )
            else:
                self.update(
                    {
                        "room_id": self.env['product.product'].search([('name', '=', 'Camping A022')])
                    }
                )

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        # sequence = self.env["pos.config"].browse([vals['pos_ids']]).name
        # if sequence == 'Pine View Restaurant':
        #     vals["new_order_no"] = self.env["ir.sequence"].next_by_code('pvk.sequence') or _('New')
        # elif sequence == 'Big Party Tent':
        #     vals["new_order_no"] = self.env["ir.sequence"].next_by_code('bpt.sequence') or _('New')

        # Sequence of hotel order but prefix and padding from pos restaurant
        sequence = self.env["pos.config"].browse([vals['pos_ids']]).sequence_id
        ir_sequence_obj = self.env["ir.sequence"].search([('name', '=', 'Hotel Order')])
        ir_sequence_obj.write({
            'prefix': sequence.prefix,
            'padding': sequence.padding,
            'number_increment': sequence.number_increment,
            'number_next_actual': sequence.number_next_actual,
        })

        sequence.write({'number_next_actual': ir_sequence_obj.number_next_actual + 1})
        return super(RestaurantCustomize, self).create(vals)

    @api.constrains("table_number_ids")
    def check_table_order(self):
        for table_line in self.table_number_ids:
            if table_line.number_of_customer == 0:
                raise ValidationError(_("Please Give the Number of Guests on each Table"))

    def generate_kot(self):
        res = []
        order_tickets_obj = self.env["hotel.restaurant.kitchen.order.tickets"]
        restaurant_order_list_obj = self.env["hotel.restaurant.order.list"]
        restaurant_table_order_list_obj = self.env["hotel.table.order.list"]
        for order in self:
            if not order.order_list_ids:
                raise ValidationError(_("Please Give an Order"))
            # if not order.table_nos_ids:
            #     raise ValidationError(_("Please Assign a Table"))
            if not order.table_number_ids:
                raise ValidationError(_("Please Assign a Table"))
            table_ids = order.table_nos_ids.ids
            kot_data = order_tickets_obj.create(
                {
                    "orderno": order.order_no,
                    "kot_date": order.o_date,
                    "room_no": order.room_id.name,
                    "w_name": order.waiter_id.name,
                    "table_nos_ids": [(6, 0, table_ids)],
                }
            )

            for table_line in order.table_number_ids:
                t_line = {
                    "kot_table_order_id": kot_data.id,
                    "table_num": table_line.table_num.id,
                    "number_of_customer": table_line.number_of_customer,
                }
                restaurant_table_order_list_obj.create(t_line)
                res.append(table_line.id)

            for order_line in order.order_list_ids:
                o_line = {
                    "kot_order_id": kot_data.id,
                    "menucard_id": order_line.menucard_id.id,
                    "item_qty": order_line.item_qty,
                    "item_rate": order_line.item_rate,
                }
                restaurant_order_list_obj.create(o_line)
                res.append(order_line.id)

            order.update(
                {
                    "kitchen": kot_data.id,
                    "rest_item_id": [(6, 0, res)],
                    "state": "order",
                    "last_update_date": fields.Datetime.now(),
                }
            )
        return True

    def generate_kot_update(self):
        order_tickets_obj = self.env["hotel.restaurant.kitchen.order.tickets"]
        rest_order_list_obj = self.env["hotel.restaurant.order.list"]
        for order in self:
            line_data = {
                "orderno": order.order_no,
                "kot_date": fields.Datetime.to_string(fields.datetime.now()),
                "room_no": order.room_id.name,
                "w_name": order.waiter_id.name,
                "kot_table_list_ids": [(0, 0, {
                    'table_num': line.table_num.id,
                    'number_of_customer': line.number_of_customer,
                }) for line in order.table_number_ids if not order_tickets_obj.browse(order.kitchen).kot_table_list_ids.filtered(lambda x: x.table_num.id == line.table_num.id)],
                "table_nos_ids": [(6, 0, order.table_nos_ids.ids)],
            }

            kot_id = order_tickets_obj.browse(self.kitchen)
            kot_id.write(line_data)

            for order_line in order.order_list_ids:
                if order_line.id not in order.rest_item_id.ids:
                    kot_data = order_tickets_obj.create(line_data)
                    order.kitchen = kot_data.id
                    o_line = {
                        "kot_order_id": kot_data.id,
                        "menucard_id": order_line.menucard_id.id,
                        "item_qty": order_line.item_qty,
                        "item_rate": order_line.item_rate,
                    }
                    order.rest_item_id = [(4, order_line.id)]
                    rest_order_list_obj.create(o_line)
                    order.update(
                        {
                            "last_update_date": fields.Datetime.now(),
                        }
                    )

        return True

    # This is a function to create stock picking when state Done and auto Validate in stock picking
    def hotel_create_picking(self):
        pvk_location_id = self.env["stock.location"].search([('complete_name', '=', 'VKWH/Pine View Restaurant')])
        big_party_tent_location_id = self.env["stock.location"].search([('complete_name', '=', 'VKWH/Big Party Tent')])

        location_dest_id = self.env["stock.location"].search([('complete_name', '=', 'Partner Locations/Customers')])
        pvk_picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'PoS Orders (Pine View Restaurant)')])
        bpt_picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'PoS Orders (Big Party Tent)')])
        picking_obj = self.env['stock.picking']
        group_id = self.env["procurement.group"].create({'name': self.order_no})
        stock_move_line = []
        state_res = True

        for order in self.order_list_ids:
            if order.menucard_id.product_id.type == "product" or order.menucard_id.product_id.type == "consu" and order.menucard_id.product_id.bom_count:
                product_line = [0, False, {
                    'name': order.menucard_id.name,
                    'product_id': order.menucard_id.product_id.id,
                    'product_uom': order.menucard_id.uom_id.id,
                    'product_uom_qty': order.item_qty,
                    'quantity_done': order.item_qty,
                    'date': self.o_date,
                    'date_expected': self.o_date,
                    'state': 'draft',
                    'location_id': pvk_location_id.id,
                    'location_dest_id': location_dest_id.id,
                    'group_id': group_id.id
                }]
                stock_move_line.append(product_line)

        # If there are product type = 'product' in order line
        # Then create a stock picking
        if self.pos_ids.name == "Pine View Restaurant":
            if len(stock_move_line) > 0:
                picking_list = {
                    'origin': self.order_no,
                    'partner_id': False,
                    'date_done': self.o_date,
                    'move_type': 'direct',
                    'picking_type_id': pvk_picking_type_id.id,
                    'location_id': pvk_location_id.id,
                    'location_dest_id': location_dest_id.id,
                    'move_lines': stock_move_line,
                    'state': 'assigned',
                    'group_id': group_id.id,
                }
                res = picking_obj.create(picking_list)
                self.hotel_picking = res
                state_res = self._hotel_force_picking_done(res)

        elif self.pos_ids.name == "Big Party Tent":
            if len(stock_move_line) > 0:
                picking_list = {
                    'origin': self.order_no,
                    'partner_id': False,
                    'date_done': self.o_date,
                    'move_type': 'direct',
                    'picking_type_id': bpt_picking_type_id.id,
                    'location_id': big_party_tent_location_id.id,
                    'location_dest_id': location_dest_id.id,
                    'move_lines': stock_move_line,
                    'state': 'assigned',
                    'group_id': group_id.id,
                }
                res = picking_obj.create(picking_list)
                self.hotel_picking = res
                state_res = self._hotel_force_picking_done(res)
        return state_res

    # force state in stock picking to done
    def _hotel_force_picking_done(self, picking):
        result = True
        self.ensure_one()
        picking.action_assign()
        picking.action_done()
        # [2] check if stock picking is already validate yet
        # call when create table order for the first time
        # if picking.state == "confirmed":
        #     result = False
        return result

    # required field based on source location
    def _check_warehouse_location(self):
        warehouse = ['vKirirom']
        if self.picking_type_id.name == "PoS Orders (Pine View Restaurant)" or self.picking_type_id.name == "PoS Orders (Big Party Tent)" and self.picking_type_id.warehouse_id.name in warehouse:
            self.boolean_required = True
        else:
            self.boolean_required = False

    def done_order_kot(self):
        hsl_obj = self.env["hotel.service.line"]
        so_line_obj = self.env["sale.order.line"]
        check_stock = False
        # in order to update to kot
        self.generate_kot_update()
        if not self.hotel_picking.name:
            check_stock = self.hotel_create_picking()
        else:

            stock_picking_obj = self.env['stock.picking'].search([('name', '=', self.hotel_picking.name)])
            # [1] check if stock picking is already validate yet
            # called when stock picking is already created
            # if stock_picking_obj.state == "done":
            check_stock = True
            # else:
            #     check_stock = False

        # checking if product available in stock or not
        if check_stock:
            for order_obj in self:
                for order in order_obj.order_list_ids:
                    if order_obj.folio_id:
                        values = {
                            "order_line": order.id,
                            "order_id": order_obj.folio_id.order_id.id,
                            "name": order.menucard_id.name,
                            "product_id": order.menucard_id.product_id.id,
                            "product_uom": order.menucard_id.uom_id.id,
                            "product_uom_qty": order.item_qty,
                            "price_unit": order.item_rate,
                            "discount": order.discount_lst,
                            "price_subtotal": order.price_subtotal,
                        }
                        sol_rec = so_line_obj.create(values)
                        hsl_obj.create(
                            {
                                "folio_id": order_obj.folio_id.id,
                                "service_line_id": sol_rec.id,
                            }
                        )
                        order_obj.folio_id.write(
                            {"hotel_restaurant_orders_ids": [(4, order_obj.id)]}
                        )
            self.write({"state": "done"})
            self.auto_create_bom_product()
        else:
            self.write({"state": "waiting"})

            message_id = self.env['message.wizard'].create({'message': _(
                """Please Validate stock picking first."""
            )})
            return {
                'name': _('Product unavailable in Stock'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'message.wizard',
                'res_id': message_id.id,
                'target': 'new'
            }
        return True

    def done_cancel(self):
        """
        This method is used to change the state
        to cancel of the hotel restaurant order
        and service line from Folio
        ----------------------------------------
        @param self: object pointer
        """
        ids = []
        for line in self.order_list_ids:
            ids.append(line.id)

        for line in self.folio_id.service_line_ids:
            if line.order_line in ids:
                line.unlink()
        self.write({"state": "cancel"})
        return True

    # Delete Table Order
    def unlink(self):
        for rec in self:
            raise ValidationError(_('You can not delete Table Order in %s\
                                state.') % (rec.state))
        return super(RestaurantCustomize, self).unlink()

    # function for auto create to manufacturing
    # Update data into manufacturing Wizard
    def call_do_produce(self, mrp):
        mrp_bom_obj = self.env['mrp.bom']
        product_mrp = mrp_bom_obj.search([("product_tmpl_id", "=", mrp.product_id.name)])
        consumption = product_mrp.consumption
        components = []
        values = {
            'serial': False,
            'company_id': self.company_id.id,
            'production_id': mrp.id,
            'product_id': mrp.product_id.id,
            'qty_producing': mrp.product_qty,
            'product_uom_id': mrp.product_uom_id.id,
            'consumption': consumption,
        }
        for order in mrp:
            for com in order.move_raw_ids:
                components.append(
                    (
                        0,
                        0,
                        {
                            "company_id": self.company_id.id,
                            "product_id": com.product_id.id,
                            "qty_to_consume": com.product_uom_qty,
                            "qty_reserved": com.product_uom_qty,
                            "qty_done": com.product_uom_qty,
                            "product_uom_id": com.product_uom.id,

                        }
                    )
                )

        values.update({"raw_workorder_line_ids": components})
        mrp_pruduct_produce = self.env['mrp.product.produce'].create(values)
        mrp_pruduct_produce.do_produce()
        return True

    # Force State Manufacturing order to done
    def _force_manufacturing_done(self, mrp):
        """Force Manufacturing in order to be set as done."""
        self.ensure_one()
        mrp.action_confirm()
        mrp.action_assign()
        self.call_do_produce(mrp)
        mrp.button_mark_done()
        return True

    # This is a function for auto create in manufacturing if bom product exist
    def auto_create_bom_product(self):
        mrp_product_obj = self.env['mrp.production']
        mrp_bom_obj = self.env['mrp.bom']
        product_obj = self.env['product.product']
        stock_location_obj = self.env['stock.location']
        for order in self:
            filter_product = order.order_list_ids.filtered(lambda l: l.menucard_id.type in ['product', 'consu'] and l.menucard_id.bom_count != 0 and not float_is_zero(l.item_qty, precision_rounding=l.menucard_id.uom_id.rounding))
            for line in filter_product:
                date_planned_finish = order.o_date + timedelta(hours=1)
                component_line = []
                product_mrp = mrp_bom_obj.search([("product_tmpl_id", "=", line.menucard_id.name)])
                # product from hotel different from product.product
                product_product = product_obj.search([("name", "=", line.menucard_id.name)])
                product_uom_id = product_mrp.product_uom_id.id
                picking_type_id = product_mrp.picking_type_id
                lsource_id = picking_type_id.default_location_src_id.id
                ldestination_id = stock_location_obj.search([("complete_name", "=", "Virtual Locations/A2A Town (Cambodia) Co., Ltd.: Production")])
                product_lines_vals = {
                    "is_locked": True,
                    "product_qty": line.item_qty,
                    "date_planned_start": order.o_date,
                    "date_planned_finished": date_planned_finish,
                    "user_id": self.user_id.id,
                    "company_id": self.company_id.id,
                    "picking_type_id": picking_type_id.id,
                    "location_src_id": ldestination_id.id,
                    "location_dest_id": lsource_id,
                    "product_id": product_product.id,
                    "product_uom_id": product_uom_id,
                    "bom_id": product_mrp.id,
                }

                # looping component of bom and calculate item qty
                for bom in product_mrp:
                    for com in bom.bom_line_ids:
                        sum_product_qty = com.product_qty * line.item_qty
                        component_line.append(
                            (
                                0,
                                0,
                                {
                                    "name": "New",
                                    "date": order.o_date,
                                    "company_id": self.company_id.id,
                                    "date_expected": order.o_date,
                                    "product_id": com.product_id.id,
                                    "product_uom": com.product_uom_id.id,
                                    "product_uom_qty": sum_product_qty,
                                    "location_id": lsource_id,
                                    "location_dest_id": ldestination_id.id,
                                    "picking_type_id": picking_type_id.id,
                                }
                            )
                        )

                product_lines_vals.update({"move_raw_ids": component_line})
                mrp = mrp_product_obj.create(product_lines_vals)
                self._force_manufacturing_done(mrp)
        return True


class RestaurantCustomizeOrderList(models.Model):
    _inherit = 'hotel.restaurant.order.list'

    discount_lst = fields.Float(string="Discount", readonly=False)

    @api.depends("item_qty", "item_rate")
    def _compute_price_subtotal(self):
        for line in self:
            discount = (line.item_rate * line.item_qty) * (line.discount_lst / 100)
            line.price_subtotal = (line.item_rate * int(line.item_qty)) - discount


class SaleOrderLineCancelInherit(models.Model):
    _inherit = 'sale.order.line'

    order_line = fields.Integer(string="No")


class HotelMenucardTypeInherit(models.Model):
    _inherit = 'hotel.menucard.type'

    product_categ_id = fields.Many2one(
        "product.category", "Product Category", delegate=True
    )

    @api.model
    def create(self, vals):
        if "menu_id" in vals:
            menu_categ = self.env["hotel.menucard.type"].browse(
                vals.get("menu_id")
            )
            vals.update({"parent_id": menu_categ.product_categ_id.id})
            res = super(HotelMenucardTypeInherit, self).create(vals)
            for value in res:
                value.product_categ_id.update({'name': value.name})
        return res

    def write(self, vals):
        if "menu_id" in vals:
            menu_categ = self.env["hotel.menucard.type"].browse(
                vals.get("menu_id")
            )
            vals.update({"parent_id": menu_categ.product_categ_id.id})
        self.product_categ_id.update({'name': vals.get("name")})
        return super(HotelMenucardTypeInherit, self).write(vals)


class HotelMenucardInherit(models.Model):
    _inherit = 'hotel.menucard'

    khmer_name = fields.Char("Khmer name")

    @api.model
    def create(self, vals):
        product_categ_id = 1
        if "categ_id" in vals:
            menu_categ = self.env["hotel.menucard.type"].browse(
                vals.get("categ_id")
            )
        product_categ_id = menu_categ.product_categ_id
        res = super(HotelMenucardInherit, self).create(vals)
        for menucard in res:
            menucard.product_id.product_tmpl_id.update(
                {"categ_id": product_categ_id, "khmer_name": menucard.khmer_name, "menu_card_id": menucard})
        return res

    def write(self, vals):
        if not self._context.get("from_inventory"):
            if "khmer_name" in vals:
                self.product_id.product_tmpl_id.update({"khmer_name": vals["khmer_name"]})
            if "categ_id" in vals:
                menu_categ = self.env["hotel.menucard.type"].browse(
                    vals.get("categ_id")
                )
                product_categ_id = menu_categ.product_categ_id
                self.product_id.product_tmpl_id.update({"categ_id": product_categ_id})

        return super(HotelMenucardInherit, self).write(vals)


class HotelServiceTypeInherit(models.Model):
    _inherit = "hotel.service.type"

    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.service_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.parent_id
            return res

        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]


class HotelRoomAmenitiesType(models.Model):
    _inherit = "hotel.room.amenities.type"

    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.amenity_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.parent_id
            return res

        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]


# To identify when product create in Food Items
class ProductProduct(models.Model):

    _inherit = "product.product"

    # food item
    isfooditem = fields.Boolean("Is Food Item")


# new one2many model field
class TableOrderLine(models.Model):
    _name = "hotel.table.order.list"

    kot_table_order_id = fields.Many2one(
        "hotel.restaurant.kitchen.order.tickets", "Kitchen Table Order Tickets"
    )
    table_order_id = fields.Many2one("hotel.restaurant.order", "New Restaurant Order")
    table_num = fields.Many2one("hotel.restaurant.tables", "Table Number", required=True)
    number_of_customer = fields.Integer("Number of Guest", required=True, copy=False, default=0)


class HotelRestaurantKitchenOrderTicketsInherit(models.Model):

    _inherit = "hotel.restaurant.kitchen.order.tickets"

    kot_table_list_ids = fields.One2many(
        "hotel.table.order.list",
        "kot_table_order_id",
        "Table Order List",
        help="Kitchen table order list",
    )
