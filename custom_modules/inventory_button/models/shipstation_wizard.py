from odoo import models, fields, api


class ShipstationOption(models.Model):
    _name = "shipstation.option"
    _description = "Shipstation Option"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Shipstation code must be unique!"),
    ]


class ShipstationSelectionWizard(models.TransientModel):
    _name = "shipstation.selection.wizard"
    _description = "Shipstation Selection Wizard"

    product_id = fields.Many2one("api.product", string="Product", required=True)
    shipstation_ids = fields.Many2many(
        "shipstation.option",
        string="Shipstations",
        required=True,
    )

    new_shipstation = fields.Char(string="Add New Shipstation")

    @api.model
    def default_get(self, fields_list):
        # Populate default shipstation options if they don't exist yet
        res = super(ShipstationSelectionWizard, self).default_get(fields_list)

        # Check if shipstation options exist, if not create them
        options = self.env["shipstation.option"].search([])
        if not options:
            default_options = []
            for option in default_options:
                self.env["shipstation.option"].create(option)

        return res

    def create_shipstation(self):
        """Create a new shipstation option"""
        self.ensure_one()

        if not self.new_shipstation:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Name Provided",
                    "message": "Please enter a name for the new shipstation",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Create a code from the name (lowercase, replace spaces with underscores)
        code = self.new_shipstation.lower().replace(" ", "_")

        # Check if code already exists
        existing = self.env["shipstation.option"].search([("code", "=", code)])
        if existing:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Already Exists",
                    "message": f"A shipstation with code '{code}' already exists",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Create the new shipstation
        new_option = self.env["shipstation.option"].create(
            {
                "name": self.new_shipstation,
                "code": code,
            }
        )

        # Show success notification
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "simple_notification",
            {
                "title": "Shipstation Created",
                "message": f"Added new shipstation: {new_option.name}",
                "type": "success",
            },
        )

        # Reload the wizard to refresh the list of shipstations
        return {
            "type": "ir.actions.act_window",
            "name": "Select Shipstation",
            "res_model": "shipstation.selection.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_id": self.product_id.id,
                "default_shipstation_ids": [
                    (4, new_option.id)
                ],  # Pre-select the new shipstation
            },
            "flags": {"initial_mode": "edit"},
        }

    def action_confirm(self):
        """Process the selected shipstations"""
        self.ensure_one()

        if not self.shipstation_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Selection",
                    "message": "Please select at least one shipstation",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Get selected shipstation names
        selected_shipstations = self.shipstation_ids.mapped("name")

        # Update the product record with feedback
        if self.product_id and selected_shipstations:
            message = (
                f"Product sent to shipstations: {', '.join(selected_shipstations)}"
            )
            self.product_id.message_post(body=message)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Shipstations Selected",
                "message": f"Selected shipstations: {', '.join(selected_shipstations)}",
                "type": "success",
                "sticky": False,
            },
        }

    def action_delete_selected(self):
        """Delete selected shipstation options"""
        self.ensure_one()

        if not self.shipstation_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Selection",
                    "message": "Please select at least one shipstation to delete",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Store names for notification
        selected_names = self.shipstation_ids.mapped("name")
        count = len(selected_names)

        # Delete the selected shipstations
        self.shipstation_ids.unlink()

        # Show notification
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "simple_notification",
            {
                "title": "Shipstations Deleted",
                "message": f"Successfully deleted {count} shipstation(s)",
                "type": "success",
            },
        )

        # Reload the wizard to refresh the list
        return {
            "type": "ir.actions.act_window",
            "name": "Select Shipstation",
            "res_model": "shipstation.selection.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_id": self.product_id.id,
            },
            "flags": {"initial_mode": "edit"},
        }
