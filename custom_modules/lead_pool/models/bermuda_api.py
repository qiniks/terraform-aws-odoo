# -*- coding: utf-8 -*-

import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BermudaRaterAPI(models.AbstractModel):
    _name = "bermuda.rater.api"
    _description = "Bermuda Rater API Integration"

    @api.model
    def call_open_transaction(self, lead):
        """Call the Bermuda Rater OpenTransaction API to send a quote to a customer"""
        try:
            # This is a placeholder for the actual API call
            # In a real implementation, you would:
            # 1. Get the API credentials from Odoo config parameters
            # 2. Format the lead data according to the API requirements
            # 3. Make the API call with proper error handling

            api_url = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(
                    "bermuda_rater.api_url",
                    "https://api.bermudarater.example.com/open-transaction",
                )
            )
            api_key = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("bermuda_rater.api_key", "demo_key")
            )

            # Log the API call attempt
            _logger.info("Calling Bermuda Rater API for lead: %s", lead.name)

            # Prepare lead data for the API call
            payload = {
                "lead_id": lead.id,
                "name": lead.name,
                "email": lead.email_from or "",
                "phone": lead.phone or "",
                "company": lead.partner_name or "",
                "agent_id": lead.user_id.id,
                "agent_name": lead.user_id.name,
                "company_id": lead.company_id.id,
                "company_name": lead.company_id.name,
            }

            # Simulated API call for demonstration
            # In a real implementation, you would use:
            # response = requests.post(api_url, json=payload, headers={'Authorization': f'Bearer {api_key}'})

            # For demo, just log that we would make the call
            _logger.info("API payload: %s", payload)

            # Simulate a successful response
            return {
                "success": True,
                "transaction_id": f"TR-{lead.id}-{lead.user_id.id}",
                "message": "Quote sent successfully",
            }

        except Exception as e:
            _logger.error("Error calling Bermuda Rater API: %s", str(e))
            return {"success": False, "message": f"API Error: {str(e)}"}
