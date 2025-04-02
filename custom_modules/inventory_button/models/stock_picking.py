from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_custom_button(self):
        """
        Custom action to be performed when the button is clicked
        Calls the API and stores the data
        """
        self.ensure_one()
        try:
            # Call the method from api.product model to fetch and store data
            return self.env["api.product"].fetch_and_store_api_data()
        except Exception as e:
            _logger.error("Error in API call: %s", str(e))
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": f"Failed to retrieve API data: {str(e)}",
                    "sticky": True,
                    "type": "danger",
                },
            }
