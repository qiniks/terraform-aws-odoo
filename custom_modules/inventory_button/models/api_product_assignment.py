from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ApiProduct(models.Model):
    _inherit = "api.product"

    # Designer assignments related functionality
    designer_assigned_products = fields.Many2many(
        "api.product",
        string="Designer's Other Assignments",
        compute="_compute_designer_assigned_products",
    )

    @api.depends("designer_id")
    def _compute_designer_assigned_products(self):
        for record in self:
            if record.designer_id:
                record.designer_assigned_products = self.search(
                    [
                        ("designer_id", "=", record.designer_id.id),
                        ("id", "!=", record.id),
                    ]
                )
            else:
                record.designer_assigned_products = False

    # Update method to assign current user as designer
    def assign_to_me(self):
        for record in self:
            if record.designer_id:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Already Assigned",
                        "message": f"This order is already assigned to {record.designer_id.name}",
                        "type": "warning",
                        "sticky": False,
                    },
                }

            # Get the current user's designer record
            current_user = self.env.user
            designer = self.env["inventory.designer"].search(
                [("user_id", "=", current_user.id)], limit=1
            )

            if not designer:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Not a Designer",
                        "message": "You don't have a designer profile. Please contact an administrator.",
                        "type": "warning",
                        "sticky": False,
                    },
                }

            # Check if the current designer already has active orders
            active_orders = self.env["api.product"].search(
                [
                    ("designer_id", "=", designer.id),
                    ("state", "not in", ["approving", "done"]),
                    ("id", "!=", record.id),
                ]
            )

            if active_orders:
                # Designer already has active orders
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Order Limit Reached",
                        "message": "You can only work on one order at a time. Please complete your current order before taking a new one.",
                        "type": "warning",
                        "sticky": False,
                    },
                }  # If no active orders, assign to the current designer and set assignment date
            record.write(
                {"designer_id": designer.id, "assignment_date": fields.Datetime.now()}
            )

        return True

    def remove_assignment(self):
        """Remove designer assignment if current user is the assigned designer or an admin"""
        for record in self:
            current_user = self.env.user
            is_admin = current_user.has_group("base.group_system")
            is_assigned_user = (
                record.designer_id and record.designer_id.user_id.id == current_user.id
            )

            if is_admin or is_assigned_user:
                record.designer_id = False
                # Don't return notification here to allow the page to refresh
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Permission Denied",
                        "message": "Only the assigned designer or an administrator can remove assignment",
                        "type": "warning",
                        "sticky": False,
                    },
                }
        return True

    def action_open_designer(self):
        """Open the designer's form view"""
        self.ensure_one()
        if not self.designer_id:
            return

        return {
            "type": "ir.actions.act_window",
            "res_model": "inventory.designer",
            "view_mode": "form",
            "res_id": self.designer_id.id,
            "target": "current",
        }

    def open_shipstation_selection(self):
        """Open the shipstation selection wizard"""
        self.ensure_one()
        return {
            "name": "Select Shipstation",
            "type": "ir.actions.act_window",
            "res_model": "shipstation.selection.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_id": self.id,
            },
        }
