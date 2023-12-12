import time

from datetime import datetime, timedelta
from odoo import _, api, fields, models
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from odoo.exceptions import UserError, ValidationError, except_orm
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt


class HotelInherit(models.Model):
    _inherit = "hotel.reservation"

    booking = fields.Char(related='create_uid.name',
                        inherit=True, readonly=False)
    ref_booking = fields.Char('Ref Booking')
    date_order = fields.Datetime(
        "Date Ordered",
        readonly=True,
        required=True,
        index=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: fields.Datetime.now(),
    )
    checkin = fields.Datetime(
        "Expected-Date-Arrival",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=datetime.now().strftime("%Y-%m-%d 07:00:00")
    )
    checkout = fields.Datetime(
        "Expected-Date-Departure",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=(datetime.now() + timedelta(days=1)
                ).strftime("%Y-%m-%d 05:00:00")
    )

    # update ref_booking info folio
    def create_folio(self):
        hotel_folio_obj = self.env["hotel.folio"]
        folio_line_obj = self.env["folio.room.line"]
        room_reservation_line_obj = self.env['hotel.room.reservation.line']
        for reservation in self:
            folio_lines = []
            checkin_date = reservation["checkin"]
            checkout_date = reservation["checkout"]
            duration_vals = self._onchange_check_dates(
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                duration=False,
            )
            duration = duration_vals.get("duration") or 0.0
            folio_vals = {
                "date_order": reservation.date_order,
                "warehouse_id": reservation.warehouse_id.id,
                "partner_id": reservation.partner_id.id,
                "pricelist_id": reservation.pricelist_id.id,
                "partner_invoice_id": reservation.partner_invoice_id.id,
                "partner_shipping_id": reservation.partner_shipping_id.id,
                "checkin_date": reservation.checkin,
                "checkout_date": reservation.checkout,
                "duration": duration,
                "reservation_id": reservation.id,
                'ref_booking': reservation.ref_booking,
            }
            for line in reservation.reservation_line_ids:
                for r in line.reserve:
                    folio_lines.append(
                        (
                            0,
                            0,
                            {
                                "checkin_date": checkin_date,
                                "checkout_date": checkout_date,
                                "product_id": r.product_id and r.product_id.id,
                                "name": reservation["reservation_no"],
                                "price_unit": r.list_price,
                                "product_uom_qty": duration,
                                "is_reserved": True,
                            },
                        )
                    )
                    r.write({"status": "occupied", "isroom": False})
            folio_vals.update({"room_line_ids": folio_lines})
            folio = hotel_folio_obj.create(folio_vals)
            for rm_line in folio.room_line_ids:
                rm_line.product_id_change()

            # Create folio.room.line
            vals = {}
            for line_id in reservation.reservation_line_ids:
                for room in line_id.reserve:
                    vals = {
                        "room_id": room.id,
                        "check_in": reservation.checkin,
                        "check_out": reservation.checkout,
                        "folio_id": folio.id,
                    }
                    folio_line_obj.create(vals)

            line_ids = room_reservation_line_obj.search(
                [('reservation_id.id', '=', self.id)])
            for line in line_ids:
                line.unlink()

            self.write({"folios_ids": [(6, 0, folio.ids)], "state": "done"})
        return True


# Hotel Reservation RoomType
class HotelReservationLineInherit(models.Model):
    _inherit = "hotel_reservation.line"

    categ_id = fields.Many2one("hotel.room.type", "Room Type",
                            domain=[('complete_name', 'ilike', 'vK Services / Accommodation /')])


class ServiceLine(models.Model):
    _inherit = 'hotel.service.line'
    line_payment = fields.Selection([('cash', 'Cash'),
                                    ('credit_card', 'Credit Card'),
                                    ('cityledger', 'City Ledger'),
                                    ('foc', 'FOC')],
                                    'Payment Method', default='cityledger')


class FolioLine(models.Model):
    _inherit = 'hotel.folio.line'
    line_payment = fields.Selection([('cash', 'Cash'),
                                    ('credit_card', 'Credit Card'),
                                    ('cityledger', 'City Ledger'),
                                    ('foc', 'FOC')],
                                    'Payment Method', default='cityledger')


# Hotel Reservation Summary
class RoomReservationSummary(models.Model):
    _inherit = 'room.reservation.summary'

    date_from = fields.Datetime(
        "Date From", default=lambda self: fields.Date.today().strftime("%Y-%m-%d 16:00:00")
    )
    date_to = fields.Datetime(
        "Date To",
        default=lambda self: (
            fields.Date.today() + relativedelta(days=30)).strftime("%Y-%m-%d 16:00:00"),
    )
    room_type_summary = fields.Many2one('product.category', string="Room type",
                                        domain=[('complete_name', 'ilike', 'vK Services / Accommodation /')])

    @api.onchange(
        "date_from", "date_to"
    )  # noqa C901 (function is too complex)
    def get_room_summary(self):  # noqa C901 (function is too complex)
        """
        @param self: object pointer
        """
        res = {}
        all_detail = []
        room_obj = self.env["hotel.room"]
        reservation_line_obj = self.env["hotel.room.reservation.line"]
        folio_room_line_obj = self.env["folio.room.line"]
        date_range_list = []
        main_header = []
        summary_header_list = ["Rooms"]
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(
                    _("Checkout date should be greater than Checkin date.")
                )
            d_frm_obj = (datetime.strptime(str(self.date_from), dt))
            d_to_obj = (datetime.strptime(str(self.date_to), dt))
            temp_date = d_frm_obj
            while temp_date <= d_to_obj:
                val = ""
                val = (str(temp_date.strftime("%a")) + ' ' +
                    str(temp_date.strftime("%b")) + ' ' +
                    str(temp_date.strftime("%d")))
                summary_header_list.append(val)
                date_range_list.append(temp_date.strftime(dt))
                temp_date = temp_date + timedelta(days=1)
            all_detail.append(summary_header_list)

            # For Sorting By Room Type
            if not self.room_type_summary.id:
                room_ids = room_obj.search(
                    [('categ_id', 'not in', [10, 883]), ('name', 'not like', '%Camping')])
            else:
                room_ids = room_obj.search(
                    [('room_categ_id.name', 'ilike', self.room_type_summary.name)])

            all_room_detail = []
            for room in room_ids:
                room_detail = {}
                room_list_stats = []
                room_detail.update({"name": room.name or ""})
                if (
                        not room.room_reservation_line_ids
                        and not room.room_line_ids
                ):
                    for chk_date in date_range_list:
                        room_list_stats.append(
                            {
                                "state": "Free",
                                "date": chk_date,
                                "room_id": room.id,
                            }
                        )
                else:
                    for chk_date in date_range_list:
                        reserline_ids = room.room_reservation_line_ids.ids
                        reservline_ids = reservation_line_obj.search(
                            [
                                ("id", "in", reserline_ids),
                                ("check_in", "<=", chk_date),
                                ("check_out", ">=", chk_date),
                                ("state", "!=", "unassigned"),
                            ]
                        )
                        fol_room_line_ids = room.room_line_ids.ids
                        chk_state = ["draft", "cancel"]
                        folio_resrv_ids = folio_room_line_obj.search(
                            [
                                ("id", "in", fol_room_line_ids),
                                ("check_in", "<=", chk_date),
                                ("check_out", ">=", chk_date),
                            ]
                        )

                        if reservline_ids or folio_resrv_ids:
                            name = ""
                            room_name = ""
                            check_in = ""
                            check_out = ""
                            reservation = []

                            try:
                                if reserline_ids:
                                    name = reservline_ids.reservation_id.partner_id.name
                                if folio_resrv_ids:
                                    name = folio_resrv_ids.folio_id.partner_id.name
                            except Exception as e:
                                arr = []
                                id = ""
                                for i in e.value:
                                    if i.isdigit():
                                        id = id + i
                                    if i == ',':
                                        arr.append(int(id))
                                        id = ""
                                if int(id) not in arr and int(id) != "":
                                    arr.append(int(id))
                                if "hotel.room.reservation.line" in e.value:
                                    obj = folio_room_line_obj.browse(arr)
                                    for line in obj:
                                        check_in = parse(line.check_in).date()
                                        check_out = parse(
                                            line.check_out).date()
                                        room_name = line.room_id.name
                                        reservation.append(
                                            line.reservation_id.reservation_no)
                                raise except_orm(_('Error'), _(
                                    'There is duplicated reservations \n Room: %s \n Check In: %s \n Check Out: %s \n Reservation: %s , %s' % (
                                        room_name, str(check_in), str(check_out), reservation[0], reservation[1])))

                            room_list_stats.append(
                                {
                                    "state": reservline_ids.reservation_id.partner_id.name or folio_resrv_ids.folio_id.partner_id.name,
                                    "date": chk_date,
                                    "room_id": room.id,
                                    "is_draft": "No",
                                    "data_model": "",
                                    "data_id": 0,
                                }
                            )
                        else:
                            room_list_stats.append(
                                {
                                    "state": "Free",
                                    "date": chk_date,
                                    "room_id": room.id,
                                }
                            )

                room_detail.update({"value": room_list_stats})
                all_room_detail.append(room_detail)
            main_header.append({"header": summary_header_list})
            self.summary_header = str(main_header)
            self.room_summary = str(all_room_detail)
        return res
