from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class BulkActionsWizard(models.TransientModel):
    _name = "bulk.actions.wizard"
    _description = "Bulk Actions Wizard for Orders"

    # Fields for bulk actions
    action_type = fields.Selection(
        [
            ("assign", "Assign to Producer"),
            ("shipstation", "Send to ShipStation"),
        ],
        string="Action Type",
        required=True,
        default="assign",
    )

    designer_id = fields.Many2one("inventory.designer", string="Assign to Producer")

    # Fields for ShipStation
    shipstation_ids = fields.Many2many(
        "shipstation.option", string="ShipStation Accounts"
    )
    selected_order_count = fields.Integer(
        string="Selected Orders", compute="_compute_selected_orders"
    )
    show_shipstation_warning = fields.Boolean(
        compute="_compute_show_shipstation_warning"
    )
    order_ids = fields.Many2many("api.product", string="Selected Orders")

    @api.model
    def default_get(self, fields_list):
        res = super(BulkActionsWizard, self).default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        res["order_ids"] = active_ids
        return res

    @api.depends("order_ids")
    def _compute_selected_orders(self):
        for wizard in self:
            wizard.selected_order_count = len(wizard.order_ids)

    @api.depends("action_type", "order_ids")
    def _compute_show_shipstation_warning(self):
        """Show warning if any selected order is not in 'done' state when trying to send to ShipStation"""
        for wizard in self:
            if wizard.action_type == "shipstation":
                not_done_orders = wizard.order_ids.filtered(lambda o: o.state != "done")
                wizard.show_shipstation_warning = bool(not_done_orders)
            else:
                wizard.show_shipstation_warning = False

    def execute_action(self):
        """Execute the selected bulk action on all selected orders"""
        self.ensure_one()

        if not self.order_ids:
            raise UserError(_("No orders selected for bulk action."))

        if self.action_type == "assign":
            if not self.designer_id:
                raise UserError(_("Please select a producer to assign the orders to."))

            # Assign the selected designer to all selected orders
            self.order_ids.write(
                {
                    "designer_id": self.designer_id.id,
                    "assignment_date": fields.Datetime.now(),
                }
            )

            # Log the bulk assignment in chatter for each order
            for order in self.order_ids:
                order.message_post(
                    body=_("Order assigned to %s via bulk assignment")
                    % self.designer_id.name,
                    message_type="notification",
                )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Assignment Complete"),
                    "message": _("%s orders assigned to %s")
                    % (len(self.order_ids), self.designer_id.name),
                    "sticky": False,
                    "type": "success",
                },
            }

        elif self.action_type == "shipstation":
            if not self.shipstation_ids:
                raise UserError(_("Please select at least one ShipStation account."))

            # Only process orders in 'done' state
            orders_to_process = self.order_ids.filtered(lambda o: o.state == "done")

            if not orders_to_process:
                raise UserError(
                    _(
                        "None of the selected orders are in 'Done' status. Only completed orders can be sent to ShipStation."
                    )
                )

            # Call method to send orders to ShipStation
            result = self._send_to_shipstation(orders_to_process)

            return result

    def _send_to_shipstation(self, orders):
        """Send all selected orders to selected ShipStation accounts"""
        try:
            # Track successfully sent orders
            success_count = 0
            failed_orders = []

            for order in orders:
                try:
                    # Associate order with selected ShipStation accounts
                    order.write(
                        {
                            "shipstation_ids": [(6, 0, self.shipstation_ids.ids)],
                            "state": "synced_with_shipstation",  # Update the state
                            "shipstation_status": "synced",
                            "shipstation_sync_date": fields.Datetime.now(),
                        }
                    )

                    # Call the export to ShipStation method
                    # Note: This would be replaced with actual ShipStation API logic
                    # For now, we're just simulating the API call
                    order.message_post(
                        body=_("Order sent to ShipStation accounts: %s")
                        % ", ".join(self.shipstation_ids.mapped("name")),
                        message_type="notification",
                    )

                    success_count += 1

                except Exception as e:
                    _logger.error(
                        f"Failed to send order {order.name} to ShipStation: {str(e)}"
                    )
                    failed_orders.append(order.name)

            # Create the result message
            if failed_orders:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Partial Success"),
                        "message": _(
                            "%s orders sent to ShipStation successfully. Failed orders: %s"
                        )
                        % (success_count, ", ".join(failed_orders)),
                        "sticky": True,
                        "type": "warning",
                    },
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Success"),
                        "message": _("%s orders sent to ShipStation successfully")
                        % success_count,
                        "sticky": False,
                        "type": "success",
                    },
                }

        except Exception as e:
            _logger.error(f"Error in bulk ShipStation processing: {str(e)}")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Error processing ShipStation integration: %s")
                    % str(e),
                    "sticky": True,
                    "type": "danger",
                },
            }
