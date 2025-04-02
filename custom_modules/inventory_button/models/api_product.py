from odoo import models, fields, api
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

data = [
    {"id": 1, "name": "T-Shirt", "date": "2025-03-01", "design": "Modern"},
    {"id": 2, "name": "Shirt", "date": "2025-03-02", "design": "Classic"},
    {"id": 3, "name": "T-Shirt", "date": "2025-03-03", "design": "Minimal"},
    {"id": 4, "name": "Shirt", "date": "2025-03-04", "design": "Vintage"},
    {"id": 5, "name": "T-Shirt", "date": "2025-03-05", "design": "Abstract"},
    {"id": 6, "name": "Shirt", "date": "2025-03-06", "design": "Geometric"},
    {"id": 7, "name": "T-Shirt", "date": "2025-03-07", "design": "Floral"},
    {"id": 8, "name": "Shirt", "date": "2025-03-08", "design": "Industrial"},
    {"id": 9, "name": "T-Shirt", "date": "2025-03-09", "design": "Scandinavian"},
    {"id": 10, "name": "Shirt", "date": "2025-03-10", "design": "Bohemian"},
    {"id": 11, "name": "T-Shirt", "date": "2025-03-11", "design": "Rustic"},
    {"id": 12, "name": "Shirt", "date": "2025-03-12", "design": "Contemporary"},
    {"id": 13, "name": "T-Shirt", "date": "2025-03-13", "design": "Eclectic"},
    {"id": 14, "name": "Shirt", "date": "2025-03-14", "design": "Art Deco"},
    {"id": 15, "name": "T-Shirt", "date": "2025-03-15", "design": "Retro"},
    {"id": 16, "name": "Shirt", "date": "2025-03-16", "design": "Futuristic"},
    {"id": 17, "name": "T-Shirt", "date": "2025-03-17", "design": "Baroque"},
    {"id": 18, "name": "Shirt", "date": "2025-03-18", "design": "Gothic"},
    {"id": 19, "name": "T-Shirt", "date": "2025-03-19", "design": "Tropical"},
    {"id": 20, "name": "Shirt", "date": "2025-03-20", "design": "Nautical"},
    {"id": 21, "name": "T-Shirt", "date": "2025-03-21", "design": "Urban"},
    {"id": 22, "name": "Shirt", "date": "2025-03-22", "design": "Traditional"},
    {"id": 23, "name": "T-Shirt", "date": "2025-03-23", "design": "Mid-Century"},
    {"id": 24, "name": "Shirt", "date": "2025-03-24", "design": "Pop Art"},
    {"id": 25, "name": "T-Shirt", "date": "2025-03-25", "design": "Country"},
    {"id": 26, "name": "Shirt", "date": "2025-03-26", "design": "Shabby Chic"},
    {"id": 27, "name": "T-Shirt", "date": "2025-03-27", "design": "Oriental"},
    {"id": 28, "name": "Shirt", "date": "2025-03-28", "design": "Mediterranean"},
    {"id": 29, "name": "T-Shirt", "date": "2025-03-29", "design": "Victorian"},
    {"id": 30, "name": "Shirt", "date": "2025-03-30", "design": "Zen"},
]


class ApiProduct(models.Model):
    _name = "api.product"
    _description = "API Product Data"
    _order = "is_converted, name"  # Default sort by conversion status then name

    api_id = fields.Integer("API ID", required=True)
    name = fields.Char("Name", required=True)
    date = fields.Date("Date")
    design = fields.Char("Design")
    is_converted = fields.Boolean("Converted to Delivery", default=False)
    status_label = fields.Char("Status", compute="_compute_status_label", store=False)
    # New field for delivery status
    delivery_status = fields.Char(
        "Delivery Status", compute="_compute_delivery_status", store=False
    )

    @api.depends("is_converted")
    def _compute_status_label(self):
        for record in self:
            if record.is_converted:
                record.status_label = "✅ Delivered"
            else:
                record.status_label = "🔄 Ready for Delivery"

    @api.depends("is_converted")
    def _compute_delivery_status(self):
        for record in self:
            if record.is_converted:
                record.delivery_status = "Already Delivered"
            else:
                record.delivery_status = "Ready for Delivery"

    @api.model
    def fetch_and_store_api_data(self):
        """Fetch data from local API and store it in the database"""
        try:
            # Using the API through Docker host
            api_url = "http://host.docker.internal:8000/api/get_data"
            try:
                response = requests.get(api_url, timeout=10)
                print("API response", response)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        return self._process_api_data(data)

                # If we reach here, the API request failed or returned unsuccessful status
                _logger.warning(
                    "API request failed. Using local JSON file as fallback."
                )
                return self._fetch_from_local_json()

            except requests.RequestException as e:
                _logger.error("API request error: %s", str(e))
                # API request failed, use local JSON file
                _logger.info("Using local JSON file as fallback")
                return self._fetch_from_local_json()

        except Exception as e:
            _logger.error("API processing error: %s", str(e))
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Processing Error",
                    "message": f"Error processing API data: {str(e)}",
                    "sticky": True,
                    "type": "danger",
                },
            }

    def _fetch_from_local_json(self):
        """Fetch a random selection of 1-5 items from the local data array"""
        try:
            import random

            # Randomly select 1 to 5 items from the data array
            num_items = random.randint(1, 5)
            # Shuffle a copy of the data array and take the first num_items elements
            selected_data = random.sample(data, min(num_items, len(data)))

            _logger.info(
                f"Using {num_items} random items from local data array as fallback"
            )

            # Create a proper structure for the data
            local_data = {
                "status": "success",
                "source": "local random",
                "data": selected_data,
            }

            return self._process_api_data(local_data)
        except Exception as e:
            _logger.error(f"Error processing local data array: {str(e)}")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": f"Failed to process local data: {str(e)}",
                    "sticky": True,
                    "type": "danger",
                },
            }

    def _process_api_data(self, data):
        """Process API data and create products"""
        products = data.get("data", [])
        created_count = 0

        for product in products:
            # Check if product already exists
            existing = self.search([("api_id", "=", product.get("id"))])
            if not existing:
                # Create new product record
                self.create(
                    {
                        "api_id": product.get("id"),
                        "name": product.get("name"),
                        "date": product.get("date"),
                        "design": product.get("design"),
                    }
                )
                created_count += 1

        # Return notification
        source = "API" if data.get("source") != "local" else "local file"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Success",
                "message": f"Successfully fetched {created_count} new products from {source}",
                "sticky": False,
                "type": "success",
            },
        }

    def create_delivery_order(self):
        """Create a delivery order for a single API product"""
        self.ensure_one()

        if self.is_converted:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Warning",
                    "message": f"Product {self.name} has already been converted to a delivery order",
                    "sticky": False,
                    "type": "warning",
                },
            }

        # Get warehouse for outgoing shipments
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        if not warehouse:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "No warehouse found to create delivery",
                    "sticky": True,
                    "type": "danger",
                },
            }

        # Create a product in Odoo's product catalog if it doesn't exist
        product = self.env["product.product"].search(
            [("name", "=", self.name)], limit=1
        )
        if not product:
            product = self.env["product.product"].create(
                {
                    "name": self.name,
                    "type": "product",
                    "categ_id": self.env.ref("product.product_category_all").id,
                }
            )

        # Create a stock picking (delivery order)
        picking_type = self.env["stock.picking.type"].search(
            [("warehouse_id", "=", warehouse.id), ("code", "=", "outgoing")], limit=1
        )

        if not picking_type:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "No outgoing operation type found",
                    "sticky": True,
                    "type": "danger",
                },
            }

        # Get explicit locations to avoid null values
        location_src = picking_type.default_location_src_id
        location_dest = picking_type.default_location_dest_id

        # Fallback to warehouse locations if default locations are not set
        if not location_src:
            location_src = warehouse.lot_stock_id
        if not location_dest:
            location_dest = self.env.ref(
                "stock.stock_location_customers", raise_if_not_found=False
            )
            if not location_dest:
                # Create a customer location if it doesn't exist
                location_dest = self.env["stock.location"].create(
                    {
                        "name": "Customers",
                        "usage": "customer",
                        "company_id": self.env.company.id,
                    }
                )

        # Verify we have valid locations
        if not location_src or not location_dest:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "Could not determine appropriate stock locations",
                    "sticky": True,
                    "type": "danger",
                },
            }

        try:
            # Create the delivery order
            picking = self.env["stock.picking"].create(
                {
                    "partner_id": self.env.user.partner_id.id,  # Use current user as partner
                    "picking_type_id": picking_type.id,
                    "location_id": location_src.id,
                    "location_dest_id": location_dest.id,
                    "origin": f"API Product {self.api_id}",
                    "scheduled_date": self.date or fields.Date.today(),
                }
            )

            # Add move line to the picking
            self.env["stock.move"].create(
                {
                    "name": self.name,
                    "product_id": product.id,
                    "product_uom_qty": 1.0,
                    "product_uom": product.uom_id.id,
                    "picking_id": picking.id,
                    "location_id": location_src.id,
                    "location_dest_id": location_dest.id,
                }
            )

            # Mark this product as converted
            self.write({"is_converted": True})

            # Open the created delivery order
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "res_id": picking.id,
                "view_mode": "form",
                "target": "current",
            }
        except Exception as e:
            _logger.error(f"Error creating delivery order: {str(e)}")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": f"Failed to create delivery order: {str(e)}",
                    "sticky": True,
                    "type": "danger",
                },
            }

    def create_delivery_orders(self):
        """Create delivery orders for multiple selected API products - one order per product"""
        # Filter out already converted products
        products_to_convert = self.filtered(lambda p: not p.is_converted)

        if not products_to_convert:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Warning",
                    "message": "All selected products have already been converted to delivery orders",
                    "sticky": False,
                    "type": "warning",
                },
            }

        created_pickings = self.env["stock.picking"]

        # Create individual deliveries for each product
        for api_product in products_to_convert:
            try:
                result = api_product.create_delivery_order()
                if (
                    isinstance(result, dict)
                    and result.get("res_model") == "stock.picking"
                    and result.get("res_id")
                ):
                    created_pickings += self.env["stock.picking"].browse(
                        result["res_id"]
                    )
            except Exception as e:
                _logger.error(
                    f"Error creating delivery for product {api_product.name}: {str(e)}"
                )

        # If no pickings created, return to the same view
        if not created_pickings:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Warning",
                    "message": "No delivery orders were created",
                    "sticky": False,
                    "type": "warning",
                },
            }

        # If only one picking was created, open it directly
        if len(created_pickings) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "res_id": created_pickings.id,
                "view_mode": "form",
                "target": "current",
            }

        # If multiple pickings were created, open the list view of stock.picking with a domain filter
        return {
            "type": "ir.actions.act_window",
            "name": "Created Delivery Orders",
            "res_model": "stock.picking",
            "domain": [("id", "in", created_pickings.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }
