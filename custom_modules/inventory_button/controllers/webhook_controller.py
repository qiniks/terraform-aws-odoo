import logging
import json

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ShipStationWebhookController(http.Controller):

    @http.route(
        ["/shipstation/webhook", "/shipstation/webhook/<string:source_identifier>"],
        type="http",
        auth="none",
        csrf=False,
        methods=["POST"],
    )
    def shipstation_webhook(self, source_identifier=None, **post):
        """Handle incoming webhooks from ShipStation

        Can be called with either:
        - /shipstation/webhook (legacy endpoint - will only work if source_identifier is in the data)
        - /shipstation/webhook/source123 (source-specific endpoint)
        """
        _logger.info(
            f"Received webhook from ShipStation for source: {source_identifier or 'unspecified'}"
        )

        try:
            # Get the data from the request - trying multiple methods to ensure we can get the data
            data = None

            # Check if content type is JSON
            content_type = request.httprequest.headers.get("Content-Type", "")
            if content_type and "application/json" in content_type.lower():
                _logger.info("Request is JSON type")
                try:
                    body = request.httprequest.data.decode("utf-8")
                    if body:
                        data = json.loads(body)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    _logger.warning(f"Failed to decode JSON body: {e}")

            # If no JSON data, check POST form data
            if not data and post:
                _logger.info("Request contains POST data")
                data = post

            # Last resort, try to read the raw body and parse it
            if not data and request.httprequest.data:
                _logger.info("Trying to read raw request body")
                try:
                    body = request.httprequest.data.decode("utf-8")
                    if body:
                        data = json.loads(body)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    _logger.warning(f"Failed to decode request body: {e}")

            _logger.info(f"Webhook data received: {data}")

            # Basic validation
            if not data:
                _logger.error("No data received in webhook")
                return json.dumps({"status": "error", "message": "No data received"})

            # Add source identifier to the data if provided in the URL
            if source_identifier:
                if isinstance(data, dict):
                    data["source_identifier"] = source_identifier
                    _logger.info(
                        f"Added source identifier from URL: {source_identifier}"
                    )
                else:
                    _logger.warning(
                        f"Could not add source_identifier to data of type {type(data)}"
                    )
            elif not isinstance(data, dict) or "source_identifier" not in data:
                # If no source identifier is provided in the URL or the data, return an error
                _logger.error("Missing source identifier in webhook request")
                return json.dumps(
                    {
                        "status": "error",
                        "message": "Missing source identifier. Please use the source-specific webhook URL.",
                    }
                )

            # Process the webhook data - call the API product model to handle it
            api_product_model = request.env["api.product"].sudo()
            result = api_product_model.process_webhook_data(data)

            # Create more detailed response message
            response_message = "Webhook processed successfully"
            if isinstance(result, dict) and "params" in result:
                if "message" in result["params"]:
                    response_message = result["params"]["message"]

            _logger.info(f"Webhook processed successfully: {result}")
            return json.dumps(
                {
                    "status": "success",
                    "message": response_message,
                    "details": str(result),
                }
            )

        except Exception as e:
            _logger.error(
                f"Error processing ShipStation webhook: {str(e)}", exc_info=True
            )
            return json.dumps({"status": "error", "message": str(e)})

    @http.route(
        "/shipstation/test",
        type="http",
        auth="none",
        csrf=False,
        methods=["POST", "GET"],
    )
    def shipstation_test(self, **post):
        """Test endpoint that supports both GET and POST requests"""
        _logger.info("Test endpoint called")

        method = request.httprequest.method
        headers = dict(request.httprequest.headers)

        response_data = {
            "status": "ok",
            "message": "Test endpoint is working",
            "method": method,
            "headers": headers,
        }

        # Include post data if available
        if post:
            response_data["post_data"] = post

        # Include JSON data if available
        content_type = request.httprequest.headers.get("Content-Type", "")
        if content_type and "application/json" in content_type.lower():
            try:
                body = request.httprequest.data.decode("utf-8")
                if body:
                    json_data = json.loads(body)
                    response_data["json_data"] = json_data
            except Exception as e:
                response_data["json_error"] = str(e)

        return json.dumps(response_data)
