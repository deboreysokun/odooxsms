odoo.define('pos_no_stock.pos_product_unavailable', function (require) {
"use strict";

    var core = require('web.core');
    var rpc = require("web.rpc");
    var models = require('point_of_sale.models');
    var Screens = require('point_of_sale.screens')
    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var _t = core._t;

    models.load_fields("product.product", ["name", "bom_count"]);

    /** Include when click on product */
    Screens.ProductScreenWidget.include({
       click_product: function(product) {

           if(product.to_weight && this.pos.config.iface_electronic_scale){
               this.gui.show_screen('scale',{product: product});
           }else if (product.qty_available <= 0 && product.type === 'product'){
              this.gui.show_popup('error',{
                 'title': _t('Quantity is not enough'),
                 'body':  _t('Cannot purchase product that not available in stock!'),
              });
           }
           else{
               this.pos.get_order().add_product(product);
           }
       },
    });

    /* Include on Payment button */
    Screens.ActionpadWidget.include({
        renderElement: async function() {
            PosBaseWidget.prototype.renderElement.call(this);
            var self = this;

            this.$('.pay').click(async function() {

                console.log(" Payment new ")
                var order = self.pos.get_order();
                var product_bom_name = "";
                var bom_component_name = "";
                var product_qty_bom = 0;

                var has_valid_product_lot = _.every(order.orderlines.models, function(line) {
                    return line.has_valid_product_lot();
                });

                var has_available_product = await Promise.all(order.orderlines.models.map(async function(line) {
                    return line.has_valid_product_lot();
                }));

                var has_bom_mrp = true; // Initialize the flag variable

                /* loop order line to check if any orderlines order qty out of stock */
                var has_available_product = _.every(order.orderlines.models, function(line) {
                    var product = line.get_product();
                    if (product.qty_available < line.get_quantity() && product.type === 'product') {
                        return false;
                    } else {
                        return true;
                    }
                });

                /* check if pos session allow auto create to manufacturing or not */
                if (self.pos.config.create_order_to_manu) {
                    /* loop order check if bom product exist and check components of BOM are all available */
                    var bomComponentPromises = order.orderlines.models.map(async function(line) {
                        var product = line.get_product();
                        var line_qty = line.get_quantity();

                        if (product.bom_count != 0 && has_bom_mrp) {
                            var bomComponents = await rpc.query({
                                model: 'mrp.bom.line',
                                method: 'search_read',
                                domain: [['bom_id.product_tmpl_id.name', '=', product.name]],
                                fields: ['product_id', 'product_qty'],
                            });


                            if (line_qty != 0) {
                                for (var component of bomComponents) {
                                    var productId = component.product_id[0];
                                    var productQty = component.product_qty;

                                    var productData = await rpc.query({
                                        model: 'product.product',
                                        method: 'read',
                                        args: [[productId], ['qty_available']],
                                    });

                                    var qtyAvailable = productData[0].qty_available;
                                    var total_produce = productQty * line_qty;

                                    if (qtyAvailable < total_produce) {
                                        var productData = await rpc.query({
                                            model: 'product.product',
                                            method: 'read',
                                            args: [[productId], ['name']],
                                        });

                                        var productName = productData[0].name;
                                        product_bom_name = product.name;
                                        bom_component_name = productName;
                                        product_qty_bom = productQty;

                                        has_bom_mrp = false; // Set the flag variable to false
                                        break; // Exit the loop
                                    }
                                }
                            }
                        }
                        return true;
                    });

                    await Promise.all(bomComponentPromises); // Wait for all the Promises to resolve
                }

                /* checking if product and BOM component available in stock */
                if (!has_available_product) {
                    self.gui.show_popup('error-sync', {
                        'title': _t('Quantity is not enough'),
                        'body': _t('Cannot purchase products that do not have enough in stock!'),
                    });
                } else if (!has_bom_mrp) {
                    self.gui.show_popup('error-sync', {
                        'title': _t('Component of a BOM product is not enough'),
                        'body': _t('Cannot produce ' + product_bom_name + ' because the component is not enough \n\n' +
                            " - " + bom_component_name),
                    });
                } else if (!has_valid_product_lot) {
                    self.gui.show_popup('confirm', {
                        'title': _t('Empty Serial/Lot Number'),
                        'body': _t('One or more product(s) require serial/lot numbers.'),
                        confirm: function() {
                            self.gui.show_screen('payment');
                        },
                        has_bom_mrp
                    });
                } else {
                    self.gui.show_screen('payment');
                }
            });

            this.$('.set-customer').click(function() {
                self.gui.show_screen('clientlist');
            });
        }
    });
});
