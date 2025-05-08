import os
from odoo import models, fields, api
import requests
import logging
from datetime import datetime
import base64
import json

_logger = logging.getLogger(__name__)


class ApiProduct(models.Model):
    _inherit = "api.product"

    item_details = fields.Text(string="Item Details JSON")
    parsed_items = fields.Html(string="All Items", compute="_compute_parsed_items")
    source_id = fields.Many2one(
        "inventory.admin.settings",
        string="API Source",
        readonly=True,
        index=True,
        tracking=True,
        help="The API source this product was fetched from",
    )
    source_identifier = fields.Char(
        related="source_id.source_identifier",
        string="Source Identifier",
        store=True,
        readonly=True,
        index=True,
    )

    @api.depends("item_details")
    def _compute_parsed_items(self):
        """Parse the item_details JSON and format it as HTML for display with clickable images."""
        for record in self:
            html_content = """
            <table class="table table-sm table-striped">
              <thead>
                <tr>
                  <th>Image</th>
                  <th>SKU</th>
                  <th>Name</th>
                  <th>Quantity</th>
                  <th>Unit Price</th>
                  <th>Options</th>
                </tr>
              </thead>
              <tbody>
            """

            if record.item_details:
                try:
                    items = json.loads(record.item_details)
                    for item in items:
                        sku = item.get("sku", "")
                        name = item.get("name", "")
                        quantity = item.get("quantity", 0)
                        unit_price = item.get("unitPrice", 0)

                        # Clickable thumbnail
                        image_url = item.get("imageUrl", "")
                        if image_url:
                            image_html = f"""
                            <a href="{image_url}" target="_blank">
                              <img
                                src="{image_url}"
                                alt="Product Image"
                                style="max-width: 150px; max-height: 150px; object-fit: contain;"
                                onerror='this.src="/inventory_button/static/img/placeholder.png";'
                              />
                            </a>
                            """
                        else:
                            image_html = "No image"

                        # Format options list
                        options_html = ""
                        if item.get("options"):
                            options_html = "<ul class='mb-0'>"
                            for option in item["options"]:
                                name_opt = option.get("name", "")
                                value_opt = option.get("value", "")
                                if name_opt and value_opt:
                                    options_html += f"<li><strong>{name_opt}:</strong> {value_opt}</li>"
                            options_html += "</ul>"

                        # Append row
                        html_content += (
                            "<tr>"
                            f"<td>{image_html}</td>"
                            f"<td>{sku}</td>"
                            f"<td>{name}</td>"
                            f"<td>{quantity}</td>"
                            f"<td>${unit_price}</td>"
                            f"<td>{options_html}</td>"
                            "</tr>"
                        )
                except Exception as e:
                    _logger.error(
                        f"Error parsing item_details for record {record.id}: {e}"
                    )
                    html_content += (
                        f"<tr><td colspan='6'>Error parsing items: {e}</td></tr>"
                    )
            else:
                html_content += (
                    "<tr><td colspan='6'>No item details available</td></tr>"
                )

            html_content += "</tbody></table>"
            record.parsed_items = html_content

    @api.model
    def process_webhook_data(self, webhook_data):
        """Process incoming webhook data from ShipStation"""
        _logger.info("Processing webhook data from ShipStation")

        try:
            # Extract source identifier from webhook if available
            source_identifier = webhook_data.get("source_identifier", None)
            source = None

            if source_identifier:
                # Find the admin settings for this source
                source = self.env["inventory.admin.settings"].search(
                    [
                        ("source_identifier", "=", source_identifier),
                        ("is_active", "=", True),
                    ],
                    limit=1,
                )

                if source:
                    _logger.info(
                        f"Webhook identified for source: {source.name} (ID: {source_identifier})"
                    )
                    # Update the last webhook trigger time
                    source.update_last_webhook()
                else:
                    _logger.warning(
                        f"Received webhook for unknown source identifier: {source_identifier}"
                    )

            # If no source found, try to find based on store_id or other identifiers in the webhook
            if not source:
                store_id = webhook_data.get("store_id")
                if store_id:
                    # Try to match with a source that has this store ID in the description or name
                    sources = self.env["inventory.admin.settings"].search(
                        [
                            "|",
                            ("name", "ilike", store_id),
                            ("description", "ilike", store_id),
                            ("is_active", "=", True),
                        ]
                    )

                    if len(sources) == 1:
                        source = sources[0]
                        _logger.info(
                            f"Matched webhook to source based on store_id: {source.name}"
                        )
                        source.update_last_webhook()

                # If still no match, use the first active source as fallback
                if not source:
                    source = self.env["inventory.admin.settings"].search(
                        [("is_active", "=", True)], limit=1
                    )

                    if source:
                        _logger.warning(
                            f"No source identifier in webhook, using default source: {source.name}"
                        )
                        source.update_last_webhook()
                    else:
                        _logger.error(
                            "No active API sources found for webhook processing"
                        )
                        return {
                            "status": "error",
                            "message": "No active API sources found for webhook processing",
                        }

            # Check for resource_type to determine what kind of webhook this is
            resource_type = webhook_data.get("resource_type")

            # If the webhook includes a resource_url, we could extract the importBatch parameter
            resource_url = webhook_data.get("resource_url", "")
            import_batch = None
            if resource_url and "importBatch=" in resource_url:
                # Extract the import batch ID from the URL
                try:
                    import_batch = resource_url.split("importBatch=")[1].split("&")[0]
                    _logger.info(f"Detected import batch ID: {import_batch}")
                except Exception as e:
                    _logger.warning(f"Could not extract import batch ID: {e}")

            if resource_type == "ORDER_NOTIFY":
                # This is a notification about an order change, fetch the latest orders
                # Get all users who should receive notifications (users with inventory access)
                message_util = self.env["inventory_button.send_message"]

                # Find all active users to notify
                users = self.env["res.users"].search([("active", "=", True)])
                notification_sent = False

                for user in users:
                    if user.partner_id:
                        # Send notification to each user with a valid partner
                        message_util.send_notification(
                            user.partner_id,
                            f"ShipStation Order Notification - {source.name}",
                            f"New order notification received from ShipStation source: {source.name}.",
                            sticky=False,
                            message_type="info",
                        )
                        notification_sent = True
                        _logger.info(f"Sent notification to user: {user.name}")

                if notification_sent:
                    _logger.info("Successfully sent ORDER_NOTIFY webhook notifications")
                else:
                    _logger.warning(
                        "No users found to notify about the ShipStation webhook"
                    )

                return self.fetch_from_source(source, import_batch=import_batch)

            elif resource_type == "ITEM_ORDER_DATA":
                # If the webhook contains the complete order data, process it directly
                return self._process_order_data(webhook_data, source)

            else:
                _logger.warning(f"Unhandled webhook resource_type: {resource_type}")
                return {
                    "status": "warning",
                    "message": f"Unhandled webhook resource type: {resource_type}",
                }

        except Exception as e:
            _logger.error(f"Error processing webhook data: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"Error processing webhook: {str(e)}"}

    def _process_order_data(self, order_data, source=None):
        """Process order data received directly from webhook"""
        # This method would handle direct order data if ShipStation sends it in the webhook
        # Implementation depends on exact webhook data structure from ShipStation
        _logger.info("Processing direct order data from webhook")

        # For now, this just triggers a regular API fetch
        if source:
            return self.fetch_from_source(source)
        else:
            return self.fetch_and_store_api_data()

    @api.model
    def fetch_from_source(self, source, import_batch=None, filter_status=True):
        """Fetch data from a specific ShipStation API source"""
        if not source:
            _logger.error("No source provided for API fetch")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "API Fetch Error",
                    "message": "No source provided for API fetch",
                    "sticky": False,
                    "type": "danger",
                },
            }

        try:
            # Use API credentials from the provided source
            api_key = source.api_key
            api_secret = source.api_secret
            url = source.api_url or "https://ssapi.shipstation.com/orders"
            source_id = source.id
            source_identifier = source.source_identifier

            if not api_key or not api_secret:
                _logger.error(f"Missing API credentials for source: {source.name}")
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "API Connection Error",
                        "message": f"Missing API credentials for source: {source.name}",
                        "sticky": True,
                        "type": "danger",
                    },
                }

            # Create authorization string (API Key:API Secret) and encode verlae it in Base64
            auth_string = f"{api_key}:{api_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            }

            # API parameters
            params = {
                "pageSize": 500,
                "sortBy": "OrderDate",
                "sortDir": "DESC",
            }

            # Apply orderStatus filter only if filter_status is True
            if filter_status:
                params["orderStatus"] = "awaiting_shipment"
                status_desc = "awaiting shipment orders"
            else:
                status_desc = "all orders (all statuses)"

            # If we have an import batch ID from the webhook, add it to the parameters
            if import_batch:
                params["importBatch"] = import_batch
                _logger.info(f"Filtering by import batch: {import_batch}")

            _logger.info(
                f"Trying to connect to ShipStation API at: {url} for source: {source.name} to fetch {status_desc}"
            )
            _logger.info(f"API parameters: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                _logger.info(
                    f"Successfully connected to ShipStation API for source: {source.name}"
                )
                # Update the last fetch time in admin settings
                source.update_last_fetch()
            else:
                _logger.error(
                    f"API returned status code: {response.status_code} for source: {source.name}"
                )
                raise ValueError(
                    f"Could not connect to API endpoint: {response.status_code}"
                )

            # Parse JSON response
            api_data = response.json()

            # Log detailed response information
            orders_count = len(api_data.get("orders", []))
            _logger.info(
                f"API response received with {orders_count} {status_desc} for source: {source.name}"
            )

            # If no orders found, log the full response for debugging (limited to prevent huge logs)
            if orders_count == 0:
                # Log first 500 chars of the response to avoid overly large logs
                response_preview = str(api_data)[:500] + (
                    "..." if len(str(api_data)) > 500 else ""
                )
                _logger.info(
                    f"API response preview for source {source.name}: {response_preview}"
                )

        except (requests.exceptions.RequestException, ValueError) as e:
            _logger.error(
                f"Could not connect to API for source {source.name}: {str(e)}"
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": f"API Connection Error - {source.name}",
                    "message": f"Could not connect to ShipStation API: {str(e)}",
                    "sticky": True,
                    "type": "danger",
                },
            }

        if "orders" in api_data:
            try:
                # Track how many products were added and updated
                added_count = 0
                updated_count = 0
                orders_processed = 0

                # Dictionary to track unique store IDs
                unique_store_ids = {}

                # First, get all order numbers from the API response for efficient batch lookup
                order_numbers = [
                    order.get("orderNumber")
                    for order in api_data["orders"]
                    if order.get("orderNumber")
                ]

                # Find all existing orders from this source in a single database query
                existing_orders = (
                    {
                        record.order_number: record
                        for record in self.search(
                            [
                                ("order_number", "in", order_numbers),
                                ("source_id", "=", source_id),
                            ]
                        )
                    }
                    if order_numbers
                    else {}
                )

                _logger.info(
                    f"Found {len(existing_orders)} existing orders in database for source: {source.name}"
                )

                for order in api_data["orders"]:
                    orders_processed += 1
                    order_id = order.get("orderId")
                    order_number = order.get("orderNumber")
                    order_status = order.get("orderStatus", "")

                    # Extract store_id from advancedOptions object
                    advanced_options = order.get("advancedOptions", {})
                    store_id = int(advanced_options["storeId"])

                    # Track unique store IDs and their names
                    if store_id and store_id not in unique_store_ids:
                        store_name = order.get("storeName", "")
                        unique_store_ids[store_id] = {
                            "storeId": store_id,
                            "storeName": store_name,
                        }

                    # Check if this order already exists for this source
                    existing_product = existing_orders.get(order_number)

                    # If order exists, only update the status if it has changed
                    if existing_product:
                        if existing_product.order_status != order_status:
                            _logger.info(
                                f"Order {order_number} status changed: {existing_product.order_status} → {order_status} for source: {source.name}"
                            )
                            existing_product.write({"order_status": order_status})
                            updated_count += 1
                        else:
                            _logger.info(
                                f"Order {order_number} status unchanged ({order_status}), skipping for source: {source.name}"
                            )
                        continue  # Skip further processing of this order

                    # Continue with processing only for new orders
                    _logger.info(
                        f"New order {order_number}, processing for source: {source.name}..."
                    )

                    # Get items count in order for logging
                    all_items = order.get("items", [])
                    items_count = len(all_items)
                    _logger.info(f"Order {order_number} contains {items_count} items")

                    # Use all items without filtering out discounts
                    items = all_items
                    if not items:
                        _logger.info(f"Order {order_number} has no items")
                        continue

                    main_item = None
                    for item in items:
                        if item.get("lineItemKey") != "Discount":
                            main_item = item
                            break

                    # If no non-discount items found, use the first item
                    if not main_item and items:
                        main_item = items[0]

                    # If there are no items at all, skip this order
                    if not main_item:
                        _logger.info(
                            f"Order {order_number} has no valid items to use as main item"
                        )
                        continue

                    api_id = main_item.get("orderItemId")

                    # Store all items as JSON for reference
                    item_details_json = json.dumps(items)

                    # Order date handling
                    order_date_str = order.get("orderDate")
                    order_date = False
                    if order_date_str:
                        try:
                            # Parse ISO format datetime - extract just the date part
                            date_part = order_date_str.split("T")[0]
                            dt = datetime.strptime(date_part, "%Y-%m-%d")
                            order_date = dt.date()
                        except (ValueError, TypeError, IndexError) as e:
                            _logger.warning(
                                f"Could not parse date {order_date_str}: {e}"
                            )
                            # Fall back to storing the raw string
                            order_date = order_date_str

                    # Ship by date handling
                    ship_by_date_str = order.get("shipByDate")
                    ship_by_date = False
                    if ship_by_date_str and order.get("orderStatus") != "cancelled":
                        try:
                            # Parse ISO format datetime - extract just the date part
                            date_part = ship_by_date_str.split("T")[0]
                            dt = datetime.strptime(date_part, "%Y-%m-%d")
                            ship_by_date = dt.date()
                        except (ValueError, TypeError, IndexError) as e:
                            _logger.warning(
                                f"Could not parse ship by date {ship_by_date_str}: {e}"
                            )
                            # Fall back to storing the raw string
                            ship_by_date = ship_by_date_str

                    # Get shipping address information
                    ship_to = order.get("shipTo", {})
                    shipping_address = ""
                    if ship_to:
                        address_parts = []
                        if ship_to.get("name"):
                            address_parts.append(ship_to.get("name"))
                        if ship_to.get("company"):
                            address_parts.append(ship_to.get("company"))
                        if ship_to.get("street1"):
                            address_parts.append(ship_to.get("street1"))
                        if ship_to.get("street2"):
                            address_parts.append(ship_to.get("street2"))
                        if ship_to.get("city"):
                            city_state = []
                            city_state.append(ship_to.get("city"))
                            if ship_to.get("state"):
                                city_state.append(ship_to.get("state"))
                            address_parts.append(", ".join(filter(None, city_state)))
                        if ship_to.get("postalCode"):
                            address_parts.append(ship_to.get("postalCode"))
                        if ship_to.get("country"):
                            address_parts.append(ship_to.get("country"))
                        shipping_address = "\n".join(filter(None, address_parts))

                    # Extract customer email and payment details
                    customer_email = order.get("customerEmail", "")
                    order_total = order.get("orderTotal", 0.0)
                    amount_paid = order.get("amountPaid", 0.0)
                    shipping_amount = order.get("shippingAmount", 0.0)
                    tax_amount = order.get("taxAmount", 0.0)
                    payment_method = order.get("paymentMethod", "")

                    # Check if this is a rush order based on shipping service
                    shipping_service = order.get("requestedShippingService", "")
                    fast_ship = False
                    if shipping_service:
                        shipping_service_lower = shipping_service.lower()
                        fast_ship = (
                            "expedited" in shipping_service_lower
                            or "priority" in shipping_service_lower
                            or "express" in shipping_service_lower
                        )
                        _logger.debug(
                            f"Shipping service: {shipping_service}, fast ship: {fast_ship}"
                        )

                    # Get customer notes
                    customer_notes = order.get("customerNotes", "")
                    notes = customer_notes
                    if order.get("internalNotes"):
                        if notes:
                            notes += "\n\n"
                        notes += f"Internal: {order.get('internalNotes')}"

                    # We already got these from main_item earlier
                    sku = main_item.get("sku", "")
                    product_name = main_item.get("name", "")
                    image_url = main_item.get("imageUrl", "")

                    _logger.info(f"Using main item: SKU={sku}, Product={product_name}")

                    # Determine total quantity across all items
                    total_quantity = sum(item.get("quantity", 0) for item in items)

                    # Extract options from the main item
                    options = main_item.get("options", [])

                    # Create a dictionary to store all options dynamically
                    item_options = {}

                    # Process all options from ShipStation response
                    for option in options:
                        option_name = option.get("name", "")
                        option_value = option.get("value", "")
                        if option_name and option_value:
                            item_options[option_name.lower()] = option_value

                    # Simply use the already parsed ship_by_date as delivery_date
                    delivery_date = ship_by_date

                    # Include source information in the product name for easy identification
                    display_name = f"{sku or product_name[:30]} [{source.name}]"

                    # Prepare values for create with all the fields
                    product_values = {
                        "api_id": api_id,
                        "name": display_name,
                        "date": order_date,
                        "design": sku,  # Using SKU as design identifier
                        "fast_ship": fast_ship,
                        "quantity": total_quantity,
                        "email": customer_email,
                        "notes": notes,
                        "photo_url": image_url,
                        "delivery_date": delivery_date,
                        "address": shipping_address,
                        # ShipStation specific fields
                        "order_id": order_id,
                        "order_number": order_number,
                        "order_date": order_date,
                        "ship_by_date": ship_by_date,
                        "order_status": order_status,
                        "customer_email": customer_email,
                        "item_details": item_details_json,
                        "sku": sku,
                        "store_id": store_id,
                        "image_url": image_url,
                        "product_name": product_name,
                        "customer_notes": customer_notes,
                        "shipping_service": shipping_service,
                        "order_total": order_total,
                        "amount_paid": amount_paid,
                        "shipping_amount": shipping_amount,
                        "tax_amount": tax_amount,
                        "shipping_address": shipping_address,
                        "payment_method": payment_method,
                        # Source information
                        "source_id": source_id,
                        "design_price": 0.0,
                    }

                    # Create new product - no need for condition since we already checked
                    _logger.info(
                        f"Creating new product for order {order_number} from source: {source.name}"
                    )
                    api_product = self.create(product_values)
                    _logger.info(
                        f"Created API product: {api_product.name}, ID: {api_product.api_id}, Order: {order_number}, Source: {source.name}"
                    )
                    added_count += 1

                # Update the orders count on the source
                if added_count > 0:
                    source.increment_orders_count(added_count)

                # Store the collected store IDs in the source settings
                if unique_store_ids:
                    # Check if the source already has store data
                    existing_stores = []
                    if source.store_ids_data:
                        try:
                            existing_stores = json.loads(source.store_ids_data)
                            existing_store_ids = {
                                store["storeId"] for store in existing_stores
                            }

                            # Add any new stores found
                            for store_id, store_info in unique_store_ids.items():
                                if store_id not in existing_store_ids:
                                    # If we don't have a store name, try to fetch it
                                    if not store_info["storeName"]:
                                        store_details = source.fetch_store_by_id(
                                            store_id
                                        )
                                        if store_details and store_details.get(
                                            "storeName"
                                        ):
                                            store_info["storeName"] = store_details.get(
                                                "storeName"
                                            )
                                    existing_stores.append(store_info)
                                    _logger.info(
                                        f"Added new store to source {source.name}: ID={store_id}, Name={store_info['storeName']}"
                                    )
                        except (ValueError, json.JSONDecodeError):
                            # Invalid JSON, replace with new data
                            existing_stores = list(unique_store_ids.values())
                    else:
                        # No existing store data, use the new data
                        existing_stores = list(unique_store_ids.values())

                    # Update the source with the updated store data
                    source.write({"store_ids_data": json.dumps(existing_stores)})
                    _logger.info(
                        f"Updated store information for source {source.name}: {len(existing_stores)} stores"
                    )

                # Update success message to show more detailed counts
                message = (
                    f"ShipStation orders processed from {source.name}: {orders_processed}. "
                    f"Products: {added_count} added, {updated_count} updated (status changed)."
                )
                if orders_processed == 0:
                    message += " No orders found for this import batch."

                _logger.info(message)
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": f"API Import - {source.name}",
                        "message": message,
                        "sticky": False,
                        "type": "success" if orders_processed > 0 else "warning",
                    },
                }
            except Exception as e:
                _logger.error(
                    f"Error in fetch_from_source for {source.name}: {e}", exc_info=True
                )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": f"Error - {source.name}",
                        "message": f"Error processing API data: {str(e)}",
                        "sticky": False,
                        "type": "danger",
                    },
                }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": f"API Error - {source.name}",
                    "message": "Invalid response format from ShipStation API: 'orders' array not found",
                    "sticky": False,
                    "type": "danger",
                },
            }

    @api.model
    def fetch_and_store_api_data(self, import_batch=None):
        """Legacy method for backward compatibility, now calls fetch_all_sources"""
        admin_settings = self.env["inventory.admin.settings"]
        return admin_settings.fetch_all_sources()
