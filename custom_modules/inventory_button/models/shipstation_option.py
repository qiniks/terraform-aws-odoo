from odoo import models, fields, api, _
import logging
import random

_logger = logging.getLogger(__name__)


class ShipstationOption(models.Model):
    _name = "shipstation.option"
    _description = "ShipStation Account"
    _order = "sequence, name"

    name = fields.Char(
        "Name", required=True, help="Display name for this ShipStation account"
    )
    code = fields.Char("Code", help="Account identifier or API key")
    sequence = fields.Integer("Sequence", default=10, help="Display sequence")
    active = fields.Boolean("Active", default=True)
    color = fields.Integer("Color", default=lambda self: random.randint(1, 11))

    # Additional fields for API integration
    api_url = fields.Char("API URL", default="https://ssapi.shipstation.com")
    api_key = fields.Char("API Key")
    api_secret = fields.Char("API Secret")

    # Statistics
    order_count = fields.Integer("Order Count", compute="_compute_order_count")
    last_sync = fields.Datetime("Last Sync")

    @api.depends()
    def _compute_order_count(self):
        """Count number of orders associated with this ShipStation account"""
        for record in self:
            record.order_count = self.env["api.product"].search_count(
                [("shipstation_ids", "in", record.id)]
            )

    def name_get(self):
        """Custom name display to include code if available"""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"{name} [{record.code}]"
            result.append((record.id, name))
        return result
