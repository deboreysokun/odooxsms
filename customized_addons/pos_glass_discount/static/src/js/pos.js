odoo.define("pos_glass_discount", function (require) {
  "use strict";

  var pos_screens = require("point_of_sale.screens");
  var pos_models = require('point_of_sale.models');
  pos_models.Orderline = pos_models.Orderline.extend({
    get_glass_disc: function () {
      return this.glass_discount || 0;
    },
    set_glass_disc: function (disc_unit) {
      var disc = Math.min(disc_unit, this.quantity);
      this.glass_discount = disc;
      this.trigger('change', this);
    },
    set_quantity: function (quantity, keep_price) {
      pos_models.Orderline.__super__.set_quantity.apply(this, arguments);
      if (this.get_glass_disc() > 0) {
        this.set_glass_disc(quantity);
      }
    },
    export_for_printing: function() {
      var json = pos_models.Orderline.__super__.export_for_printing.apply(this, arguments);
      json.glass_discount = this.get_glass_disc();
      return json;
    },
    export_as_JSON: function () {
      var json = pos_models.Orderline.__super__.export_as_JSON.apply(this, arguments);
      json.glass_discount = this.get_glass_disc();
      return json;
    },
  });
  pos_screens.NumpadWidget = pos_screens.NumpadWidget.include({
    start: function () {
      this._super();
      this.$el.find('.glass-discount').click(_.bind(this.clickEnableGlassDiscount, this));
    },
    clickEnableGlassDiscount: function () {
      var order = this.pos.get_order();
      var discount = order.selected_orderline.discount;
      var glass_discount = order.selected_orderline.glass_discount;
      var qty = order.selected_orderline.quantity;
      if (glass_discount == undefined || glass_discount == 0) {
        order.get_selected_orderline().set_glass_disc(qty);
        order.get_selected_orderline().set_discount(discount + 10);
      } else {
        order.get_selected_orderline().set_glass_disc(0);
        order.get_selected_orderline().set_discount(discount - 10);
      }
      this.trigger('change', this);
    },
  });
});
