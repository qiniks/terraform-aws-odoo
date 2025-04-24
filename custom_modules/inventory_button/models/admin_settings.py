from odoo import models, fields, api, _
import requests
import base64
import logging
import json
from datetime import datetime
import os

_logger = logging.getLogger(__name__)


class AdminSettings(models.Model):
    _name = "inventory.admin.settings"
    _description = "Inventory Admin Settings"
    _inherit = ["mail.thread"]
    _order = "sequence, id"

    name = fields.Char(string="Setting Name", required=True)
    sequence = fields.Integer(
        string="Sequence", default=10, help="Determines the display order"
    )
    is_active = fields.Boolean(string="Active", default=True)
    description = fields.Text(string="Description")
    last_updated = fields.Datetime(string="Last Updated", readonly=True)

    # Source identification
    source_identifier = fields.Char(
        string="Source Identifier",
        required=True,
        help="Unique identifier for this API source (e.g., 'shipstation-store1')",
    )

    # API credentials - simplified without encryption
    api_key = fields.Char(string="API Key", required=True)
    api_secret = fields.Char(
        string="API Secret", required=True, help="API Secret or Password"
    )

    api_url = fields.Char(
        string="API URL", default="https://ssapi.shipstation.com/orders"
    )

    # Webhook fields
    webhook_url = fields.Char(
        string="Webhook Target URL",
        help="The URL that will receive webhook events (e.g., https://yourdomain.com/shipstation/webhook)",
    )
    webhook_event = fields.Selection(
        [
            ("ORDER_NOTIFY", "Order Notify"),
            ("ITEM_ORDER_DATA", "Item Order Data"),
            ("SHIP_NOTIFY", "Ship Notify"),
        ],
        string="Webhook Event Type",
        default="ORDER_NOTIFY",
        help="The event type to subscribe to",
    )
    webhook_store_id = fields.Char(
        string="Store ID",
        help="Optional: Filter webhook events by store ID. Leave empty to receive events for all stores.",
    )
    webhook_friendly_name = fields.Char(
        string="Webhook Name",
        default="Odoo Webhook",
        help="A friendly name for this webhook subscription",
    )
    webhook_status = fields.Selection(
        [("not_setup", "Not Setup"), ("active", "Active"), ("failed", "Failed")],
        string="Webhook Status",
        default="not_setup",
        readonly=True,
    )
    webhook_subscription_id = fields.Char(
        string="Webhook Subscription ID",
        readonly=True,
        help="The ID assigned by ShipStation when the webhook was created",
    )

    # API status tracking fields
    last_fetch_date = fields.Datetime(string="Last API Fetch", readonly=True)
    last_webhook_date = fields.Datetime(string="Last Webhook Trigger", readonly=True)
    api_status = fields.Selection(
        [
            ("success", "Connected"),
            ("failed", "Connection Failed"),
            ("not_tested", "Not Tested"),
        ],
        string="API Status",
        default="not_tested",
        readonly=True,
    )
    api_status_message = fields.Text(string="API Status Details", readonly=True)

    # Stats
    orders_count = fields.Integer(
        string="Orders Count",
        default=0,
        readonly=True,
        help="Number of orders fetched from this source",
    )

    _sql_constraints = [
        (
            "unique_source_identifier",
            "UNIQUE(source_identifier)",
            "Source Identifier must be unique!",
        )
    ]

    @api.model
    def create(self, vals):
        """Override create to set last updated timestamp"""
        vals["last_updated"] = fields.Datetime.now()
        return super(AdminSettings, self).create(vals)

    def write(self, vals):
        """Override write to set last updated timestamp"""
        vals["last_updated"] = fields.Datetime.now()
        return super(AdminSettings, self).write(vals)

    def get_api_credentials(self):
        """Get API credentials for use in API calls"""
        self.ensure_one()
        return self.api_key, self.api_secret

    def test_api_connection(self):
        """Test the connection to the API using stored credentials"""
        self.ensure_one()

        api_key, api_secret = self.get_api_credentials()
        if not api_key or not api_secret or not self.api_url:
            self.write(
                {
                    "api_status": "failed",
                    "api_status_message": "Missing API credentials or URL",
                }
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "API Connection Error",
                    "message": "API Key, Secret and URL are required",
                    "sticky": False,
                    "type": "danger",
                },
            }

        try:
            # Create authorization string (API Key:API Secret) and encode it in Base64
            auth_string = f"{api_key}:{api_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            }

            # Test parameters - just get a single order to verify connection
            params = {
                "pageSize": 1,
            }

            _logger.info(
                f"Testing connection to API at: {self.api_url} (Source: {self.source_identifier})"
            )
            response = requests.get(
                self.api_url, headers=headers, params=params, timeout=10
            )

            if response.status_code == 200:
                _logger.info(
                    f"Successfully connected to API for source {self.source_identifier}"
                )
                api_data = response.json()
                order_count = len(api_data.get("orders", []))

                # Update the status and last test timestamp
                self.write(
                    {
                        "api_status": "success",
                        "api_status_message": f"Connection successful. Found {order_count} orders in test response.",
                        "last_updated": fields.Datetime.now(),
                    }
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "API Connection Successful",
                        "message": f"Successfully connected to {self.name} (Source: {self.source_identifier}). Found {order_count} orders in test response.",
                        "sticky": False,
                        "type": "success",
                    },
                }
            else:
                error_message = f"API returned status code: {response.status_code}"
                _logger.error(
                    f"Connection failed for source {self.source_identifier}: {error_message}"
                )
                self.write(
                    {
                        "api_status": "failed",
                        "api_status_message": error_message,
                        "last_updated": fields.Datetime.now(),
                    }
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": f"API Connection Failed - {self.name}",
                        "message": error_message,
                        "sticky": False,
                        "type": "danger",
                    },
                }

        except Exception as e:
            error_message = f"Error connecting to API: {str(e)}"
            _logger.error(
                f"Exception connecting to source {self.source_identifier}: {error_message}"
            )
            self.write(
                {
                    "api_status": "failed",
                    "api_status_message": error_message,
                    "last_updated": fields.Datetime.now(),
                }
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": f"API Connection Error - {self.name}",
                    "message": error_message,
                    "sticky": False,
                    "type": "danger",
                },
            }

    def update_last_fetch(self):
        """Update the last fetch time"""
        self.ensure_one()
        self.write({"last_fetch_date": fields.Datetime.now()})

    def update_last_webhook(self):
        """Update the last webhook trigger time"""
        self.ensure_one()
        self.write({"last_webhook_date": fields.Datetime.now()})

    def increment_orders_count(self, count=1):
        """Increment the number of orders fetched from this source"""
        self.ensure_one()
        self.write({"orders_count": self.orders_count + count})

    def fetch_and_store_api_data(self):
        """Trigger API data fetch from the admin settings form for this source only"""
        self.ensure_one()
        api_product = self.env["api.product"]
        result = api_product.fetch_from_source(self)

        # Update API status to "tested" after fetch
        if result.get("params", {}).get("type") == "success":
            self.write(
                {
                    "api_status": "success",
                    "api_status_message": "API connected and data fetched successfully.",
                }
            )

        return result

    @api.model
    def fetch_all_sources(self):
        """Fetch data from all active API sources"""
        active_sources = self.search([("is_active", "=", True)])
        if not active_sources:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No API Sources",
                    "message": "No active API sources found. Please configure API settings.",
                    "sticky": False,
                    "type": "warning",
                },
            }

        api_product = self.env["api.product"]
        results = []
        success_count = 0
        error_count = 0
        orders_count = 0

        for source in active_sources:
            try:
                _logger.info(
                    f"Fetching data from source: {source.name} ({source.source_identifier})"
                )
                result = api_product.fetch_from_source(source)
                results.append(result)

                # Check if the fetch was successful
                if result.get("params", {}).get("type") == "success":
                    success_count += 1
                    # Extract orders processed count from the message
                    msg = result.get("params", {}).get("message", "")
                    if "orders processed:" in msg:
                        try:
                            count_str = (
                                msg.split("orders processed:")[1].split(".")[0].strip()
                            )
                            processed = int(count_str)
                            orders_count += processed
                        except (ValueError, IndexError):
                            pass
                else:
                    error_count += 1
            except Exception as e:
                _logger.error(f"Error fetching from source {source.name}: {str(e)}")
                error_count += 1

        # Return a summary notification
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "API Fetch Complete",
                "message": f"Fetched data from {len(active_sources)} sources. "
                f"Success: {success_count}, Errors: {error_count}, "
                f"Total orders processed: {orders_count}",
                "sticky": False,
                "type": "success" if error_count == 0 else "warning",
            },
        }

    def fetch_all_orders(self):
        """Fetch all orders (regardless of status) from this source"""
        self.ensure_one()
        api_product = self.env["api.product"]
        # Pass filter_status=False to disable the awaiting_shipment filter
        result = api_product.fetch_from_source(self, filter_status=False)

        # Update API status to "tested" after fetch
        if result.get("params", {}).get("type") == "success":
            self.write(
                {
                    "api_status": "success",
                    "api_status_message": "API connected and data fetched successfully.",
                }
            )

        return result

    @api.model
    def fetch_all_sources_all_orders(self):
        """Fetch all orders (regardless of status) from all active API sources"""
        active_sources = self.search([("is_active", "=", True)])
        if not active_sources:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No API Sources",
                    "message": "No active API sources found. Please configure API settings.",
                    "sticky": False,
                    "type": "warning",
                },
            }

        api_product = self.env["api.product"]
        results = []
        success_count = 0
        error_count = 0
        orders_count = 0

        for source in active_sources:
            try:
                _logger.info(
                    f"Fetching all orders from source: {source.name} ({source.source_identifier})"
                )
                # Pass filter_status=False to disable the awaiting_shipment filter
                result = api_product.fetch_from_source(source, filter_status=False)
                results.append(result)

                # Check if the fetch was successful
                if result.get("params", {}).get("type") == "success":
                    success_count += 1
                    # Extract orders processed count from the message
                    msg = result.get("params", {}).get("message", "")
                    if "orders processed:" in msg:
                        try:
                            count_str = (
                                msg.split("orders processed:")[1].split(".")[0].strip()
                            )
                            processed = int(count_str)
                            orders_count += processed
                        except (ValueError, IndexError):
                            pass
                else:
                    error_count += 1
            except Exception as e:
                _logger.error(f"Error fetching from source {source.name}: {str(e)}")
                error_count += 1

        # Return a summary notification
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "All Orders API Fetch Complete",
                "message": f"Fetched all orders from {len(active_sources)} sources. "
                f"Success: {success_count}, Errors: {error_count}, "
                f"Total orders processed: {orders_count}",
                "sticky": False,
                "type": "success" if error_count == 0 else "warning",
            },
        }

    def subscribe_webhook(self):
        """Subscribe to ShipStation webhook events"""
        self.ensure_one()

        api_key, api_secret = self.get_api_credentials()
        if not api_key or not api_secret:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Webhook Error",
                    "message": "API Key and Secret are required to subscribe to webhooks",
                    "sticky": False,
                    "type": "danger",
                },
            }

        if not self.webhook_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Webhook Error",
                    "message": "Webhook Target URL is required",
                    "sticky": False,
                    "type": "danger",
                },
            }

        try:
            # Create authorization string (API Key:API Secret) and encode it in Base64
            auth_string = f"{api_key}:{api_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            }

            # Build source-specific webhook URL by appending the source identifier
            # Check if the base URL already ends with a slash
            base_url = self.webhook_url.rstrip("/")
            source_specific_url = f"{base_url}/{self.source_identifier}"

            # Prepare webhook subscription data
            webhook_data = {
                "target_url": source_specific_url,
                "event": self.webhook_event,
                "store_id": self.webhook_store_id if self.webhook_store_id else None,
                "friendly_name": self.webhook_friendly_name
                or f"Odoo Webhook - {self.name}",
            }

            _logger.info(f"Subscribing to webhook for source {self.source_identifier}")
            _logger.info(f"Webhook data: {webhook_data}")

            # Subscribe to webhook
            webhook_url = "https://ssapi.shipstation.com/webhooks/subscribe"
            response = requests.post(
                webhook_url, headers=headers, json=webhook_data, timeout=15
            )

            if response.status_code in (200, 201):
                _logger.info(
                    f"Successfully subscribed to webhook for source {self.source_identifier}"
                )

                # Parse response to get subscription ID
                response_data = response.json()
                subscription_id = response_data.get("id")

                # Update webhook status and URL
                self.write(
                    {
                        "webhook_status": "active",
                        "webhook_subscription_id": subscription_id,
                        "webhook_url": source_specific_url,  # Store the full URL with source identifier
                        "last_updated": fields.Datetime.now(),
                    }
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Webhook Subscription Successful",
                        "message": f"Successfully subscribed to {self.webhook_event} events for {self.name}",
                        "sticky": False,
                        "type": "success",
                    },
                }
            else:
                error_message = f"Failed to subscribe to webhook. API returned status code: {response.status_code}"
                response_text = response.text
                try:
                    response_data = response.json()
                    if "message" in response_data:
                        error_message += f" - {response_data['message']}"
                except Exception:
                    error_message += f" - {response_text[:100]}"

                _logger.error(
                    f"Webhook subscription failed for source {self.source_identifier}: {error_message}"
                )

                # Update webhook status
                self.write(
                    {"webhook_status": "failed", "last_updated": fields.Datetime.now()}
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Webhook Subscription Failed",
                        "message": error_message,
                        "sticky": True,
                        "type": "danger",
                    },
                }

        except Exception as e:
            error_message = f"Error subscribing to webhook: {str(e)}"
            _logger.error(
                f"Exception during webhook subscription for source {self.source_identifier}: {error_message}"
            )

            # Update webhook status
            self.write(
                {"webhook_status": "failed", "last_updated": fields.Datetime.now()}
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Webhook Subscription Error",
                    "message": error_message,
                    "sticky": True,
                    "type": "danger",
                },
            }

    def unsubscribe_webhook(self):
        """Unsubscribe from ShipStation webhook"""
        self.ensure_one()

        api_key, api_secret = self.get_api_credentials()
        if not api_key or not api_secret:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Webhook Error",
                    "message": "API Key and Secret are required to unsubscribe from webhooks",
                    "sticky": False,
                    "type": "danger",
                },
            }

        if not self.webhook_subscription_id:
            # If we don't have a subscription ID, just reset the status
            self.write(
                {"webhook_status": "not_setup", "last_updated": fields.Datetime.now()}
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Webhook Reset",
                    "message": "Webhook configuration has been reset",
                    "sticky": False,
                    "type": "info",
                },
            }

        try:
            # Create authorization string (API Key:API Secret) and encode it in Base64
            auth_string = f"{api_key}:{api_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            }

            _logger.info(
                f"Unsubscribing from webhook for source {self.source_identifier}"
            )

            # Unsubscribe from webhook
            webhook_url = (
                f"https://ssapi.shipstation.com/webhooks/{self.webhook_subscription_id}"
            )
            response = requests.delete(webhook_url, headers=headers, timeout=15)

            if response.status_code in (200, 204):
                _logger.info(
                    f"Successfully unsubscribed from webhook for source {self.source_identifier}"
                )

                # Reset webhook status
                self.write(
                    {
                        "webhook_status": "not_setup",
                        "webhook_subscription_id": False,
                        "last_updated": fields.Datetime.now(),
                    }
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Webhook Unsubscribed",
                        "message": f"Successfully unsubscribed from webhook for {self.name}",
                        "sticky": False,
                        "type": "success",
                    },
                }
            else:
                error_message = f"Failed to unsubscribe from webhook. API returned status code: {response.status_code}"

                _logger.error(
                    f"Webhook unsubscription failed for source {self.source_identifier}: {error_message}"
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Webhook Unsubscription Failed",
                        "message": error_message,
                        "sticky": True,
                        "type": "danger",
                    },
                }

        except Exception as e:
            error_message = f"Error unsubscribing from webhook: {str(e)}"
            _logger.error(
                f"Exception during webhook unsubscription for source {self.source_identifier}: {error_message}"
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Webhook Unsubscription Error",
                    "message": error_message,
                    "sticky": True,
                    "type": "danger",
                },
            }
