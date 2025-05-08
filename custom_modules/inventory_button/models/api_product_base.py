from odoo import models, fields, api, _
import logging
import json
from datetime import timedelta

_logger = logging.getLogger(__name__)


class ApiProduct(models.Model):
    _name = "api.product"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "API Product Data"
    _order = "priority desc, design_difficulty desc, name"

    # Base fields
    api_id = fields.Integer("API ID", required=True)
    name = fields.Char("Name", required=True)

    # ShipStation Order fields - main fields that replace duplicates
    order_id = fields.Integer("Order ID", help="ShipStation order identifier")
    order_number = fields.Char(
        "Order Number", help="ShipStation order reference number"
    )

    order_status = fields.Char("Order Status", help="Current status in ShipStation")
    customer_email = fields.Char("Customer Email", help="Customer's email from order")
    item_details = fields.Text(
        "Item Details", help="JSON representation of order items"
    )
    sku = fields.Char("SKU", help="Product SKU code")
    image_url = fields.Char("Product Image URL", help="Product image from ShipStation")
    product_name = fields.Char(
        "Product Name", help="Full product name from ShipStation"
    )
    customer_notes = fields.Text("Customer Notes", help="Notes provided by customer")
    shipping_service = fields.Char(
        "Shipping Service", help="Requested shipping service"
    )

    # Additional useful ShipStation fields
    order_total = fields.Float("Order Total", help="Total amount of the order")
    amount_paid = fields.Float("Amount Paid", help="Amount paid by customer")
    shipping_amount = fields.Float("Shipping Amount", help="Cost of shipping")
    tax_amount = fields.Float("Tax Amount", help="Tax applied to the order")
    shipping_address = fields.Text("Shipping Address", help="Full shipping address")
    payment_method = fields.Char("Payment Method", help="Method of payment")

    store_id = fields.Integer("Store ID", help="ID of the store in ShipStation")
    store_name = fields.Char(
        "Store Name",
        compute="_compute_store_name",
        store=True,
        help="Name of the store in ShipStation",
    )
    store_color = fields.Char(
        "Store Color",
        compute="_compute_store_name",
        store=True,
        help="Color for the store in the UI",
    )

    # Legacy fields - still used but will get values from ShipStation equivalents
    date = fields.Date("Date", help="Order date")
    design = fields.Char("Design", help="Design identifier")
    fast_ship = fields.Boolean("Fast Ship", default=False)
    quantity = fields.Integer("Quantity", default=1)
    email = fields.Char("Email", help="Legacy email field")

    # Designer assignment - updated to use inventory.designer
    designer_id = fields.Many2one(
        "inventory.designer", string="Assigned Designer", tracking=True
    )
    user_id = fields.Many2one(
        "res.users", string="Assigned User", compute="_compute_user_id", store=True
    )

    # Assignment and completion tracking
    assignment_date = fields.Datetime(
        string="Assignment Date",
        readonly=True,
        help="Date when the designer was first assigned to this task",
        tracking=True,
    )
    completion_date = fields.Datetime(
        string="Completion Date",
        readonly=True,
        help="Date when the designer marked the design as done",
        tracking=True,
    )
    turnaround_hours = fields.Float(
        string="Turnaround Time (Hours)",
        compute="_compute_turnaround_time",
        store=True,
        help="Time taken to complete the design after assignment",
    )

    actual_start_date = fields.Datetime("Start Date")
    completion_date = fields.Datetime("Completion Date")
    deadline = fields.Datetime("Deadline", help="The deadline for task completion")
    task_type = fields.Char("Task Type", help="Type of task assigned to designer")
    rating = fields.Float("Rating", help="Product rating")

    # Changed to Float instead of Monetary, but will format display with $ sign
    design_price = fields.Float(
        string="Design Price ($)",
        help="Price for the design work in USD",
        digits=(10, 2),  # Ensures 2 decimal places for currency
    )

    # ShipStation integration fields
    shipstation_ids = fields.Many2many(
        "shipstation.option",
        string="ShipStation Accounts",
        help="ShipStation accounts this order has been sent to",
    )
    shipstation_sync_date = fields.Datetime(
        string="Last ShipStation Sync",
        readonly=True,
        help="Last time this order was synchronized with ShipStation",
    )
    shipstation_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("synced", "Synced"),
            ("error", "Error"),
        ],
        string="ShipStation Sync Status",
        default="pending",
    )

    # Added method to display formatted price with $ sign
    @api.depends("design_price")
    def _compute_design_price_display(self):
        for record in self:
            if record.design_price:
                record.design_price_display = f"${record.design_price:.2f}"
            else:
                record.design_price_display = "$0.00"

    # Virtual field for display purposes
    design_price_display = fields.Char(
        string="Design Price Display",
        compute="_compute_design_price_display",
        store=False,
    )

    unread_messages = fields.Boolean("Unread Messages", default=False)

    notes = fields.Text("Notes")
    photo_url = fields.Char("Photo URL")
    delivery_date = fields.Date("Delivery Date")
    order_date = fields.Date("Order Date", help="When the order was placed")
    ship_by_date = fields.Date("Ship By Date", help="Deadline for shipping")
    address = fields.Char("Shipping Address")

    design_difficulty = fields.Selection(
        [
            ("0", "Standard"),
            ("1", "Quick Edit"),
            ("2", "Some Effort"),
            ("3", "Time-Consuming"),
            ("4", "Complex Design"),
            ("5", "Intensive Work"),
        ],
        help="Design difficulty level",
        default="0",
        string="Design difficulty",
        tracking=True,
    )

    # State field with selection options
    state = fields.Selection(
        [
            ("all_orders", "All Orders"),
            ("processing", "Processing"),
            ("approving", "Approving"),
            ("done", "Done"),
            ("synced_with_shipstation", "Synced with ShipStation"),
        ],
        string="Status",
        default="all_orders",
        tracking=True,
        readonly=False,
        group_expand="_read_group_state",
    )

    manual_urgent = fields.Boolean(string="Manual Urgent", default=False)

    # Email communication fields
    message_subject = fields.Char(string="Message Subject", tracking=False)
    message_body = fields.Html(string="Message Body", tracking=False)

    @api.depends("designer_id")
    def _compute_user_id(self):
        for record in self:
            try:
                if record.designer_id and hasattr(record.designer_id, "user_id"):
                    record.user_id = record.designer_id.user_id
                else:
                    record.user_id = False
            except Exception as e:
                _logger.error(
                    f"Error computing user_id for record {record.id}: {str(e)}"
                )
                record.user_id = False

    # Add this method to properly expand groups in kanban
    @api.model
    def _read_group_state(self, states, domain, order):
        # Return all possible values for state field
        return [state[0] for state in self._fields["state"].selection]

    # Priority field for sorting
    priority = fields.Integer(
        string="Priority", compute="_compute_priority", store=True
    )

    # Field to sort unread messages only for assigned designer
    user_unread_priority = fields.Integer(
        string="User Unread Priority",
        compute="_compute_user_unread_priority",
        store=True,
    )

    @api.depends("unread_messages", "user_id")
    def _compute_user_unread_priority(self):
        current_user = self.env.user
        for record in self:
            # Set high priority only if unread AND assigned to current user
            if record.unread_messages and record.user_id.id == current_user.id:
                record.user_unread_priority = 100
            else:
                record.user_unread_priority = 0

    @api.depends("fast_ship", "quantity", "design", "manual_urgent")
    def _compute_priority(self):
        for record in self:
            _logger.info(f"Computing priority for record: {record}")
            # Default priority = 0
            priority = 0

            # Priority 4: Manual Urgent
            if record.manual_urgent:
                priority += 100
            # Priority 3 highest: fast_ship
            if record.fast_ship:
                priority += 50
            # Priority 2: Bulk Order (quantity > 10)
            if record.quantity > 10:
                priority += 20
            # Priority 1: Custom design
            if record.design:
                priority += 10

            record.priority = priority

    @api.model
    def create(self, vals):
        # Set default state if not provided
        if "state" not in vals:
            vals["state"] = "all_orders"
        return super(ApiProduct, self).create(vals)

    def toggle_manual_urgent(self):
        for record in self:
            record.manual_urgent = not record.manual_urgent
            # Force recompute priority when toggled directly
            record._compute_priority()
        return True

    def dummy_action(self):
        """Dummy method for status indicator buttons - does nothing but needed for the buttons to work"""
        return True

    def mark_read(self):
        """Set unread_messages to False when an order is opened"""
        for record in self:
            if record.unread_messages:
                record.write({"unread_messages": False})
        return True

    @api.depends("assignment_date", "completion_date")
    def _compute_turnaround_time(self):
        """Calculate the time taken to complete a design in hours"""
        for record in self:
            if record.assignment_date and record.completion_date:
                # Calculate time difference in hours
                delta = record.completion_date - record.assignment_date
                # Convert to hours (days * 24 + seconds/3600)
                record.turnaround_hours = delta.days * 24 + delta.seconds / 3600
            else:
                record.turnaround_hours = 0.0

    @api.depends("store_id", "source_id", "source_id.store_ids_data")
    def _compute_store_name(self):
        """Look up store name and color from source settings based on store_id"""
        for record in self:
            store_name = (
                str(record.store_id) if record.store_id else ""
            )  # Default to ID as string
            store_color = "#CCCCCC"  # Default gray color

            # Only proceed if we have both source and store_id
            if record.source_id and record.store_id:
                if record.source_id.store_ids_data:
                    try:
                        stores_data = json.loads(record.source_id.store_ids_data)
                        # Find store with matching ID
                        for store in stores_data:
                            if store.get("storeId") == record.store_id:
                                store_name = store.get("storeName", "")
                                store_color = store.get("color", "#CCCCCC")
                                break
                    except (json.JSONDecodeError, ValueError) as e:
                        _logger.warning(
                            f"Error parsing store data for source {record.source_id.name}: {e}"
                        )

            record.store_name = store_name or str(record.store_id) or ""
            record.store_color = store_color

    @api.model
    def get_all_shops(self):
        """
        Get all unique shops/stores for the shop filter dropdown
        Returns a list of dictionaries with shop details
        """
        # Query unique store IDs and names
        query = """
            SELECT DISTINCT store_id, store_name, store_color
            FROM api_product 
            WHERE store_id IS NOT NULL
            ORDER BY store_name
        """
        self.env.cr.execute(query)
        shops = self.env.cr.dictfetchall()

        return shops

    @api.model
    def generate_mock_assignment_data(self, days_range=30):
        """
        Generates mock data by randomly assigning designers to orders and simulating
        assignment and completion dates for testing statistics.

        :param days_range: Number of days in the past to distribute the assignments
        :return: Information about created mock data
        """
        import random
        from datetime import datetime, timedelta

        # Get all available designers
        designers = self.env["inventory.designer"].search([])
        if not designers:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Designers",
                    "message": "No designers found in the system to assign orders to",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Get unassigned orders
        unassigned_orders = self.search(
            [("designer_id", "=", False), ("state", "!=", "done")]
        )

        # Count existing orders with designers
        assigned_orders = self.search([("designer_id", "!=", False)])

        # Set up counters for summary
        assigned_count = 0
        completed_count = 0
        processing_count = 0
        approving_count = 0
        now = datetime.now()

        # State distribution for new assignments (percentages)
        state_distribution = {
            "processing": 20,  # 20% chance for processing state
            "approving": 30,  # 30% chance for approving state
            "done": 50,  # 50% chance for done state
        }

        # Process all unassigned orders
        for order in unassigned_orders:
            # Randomly decide whether to assign it (80% chance)
            if random.random() < 0.8:
                # Pick a random designer
                designer = random.choice(designers)
                # Use the order date instead of a random date
                if order.order_date:
                    # Set assignment date to the same date as the order date, with a random time
                    base_date = datetime.combine(order.order_date, datetime.min.time())
                    # Add random hours (between 9am-5pm business hours)
                    random_hour = random.randint(9, 17)
                    random_minute = random.randint(0, 59)
                    assignment_date = base_date + timedelta(
                        hours=random_hour, minutes=random_minute
                    )
                else:
                    # Fallback to current date if no order date
                    assignment_date = now

                # Determine which state to use based on our distribution
                random_num = random.random() * 100  # 0-100
                cumulative = 0
                selected_state = "all_orders"  # Default fallback

                for state, percentage in state_distribution.items():
                    cumulative += percentage
                    if random_num <= cumulative:
                        selected_state = state
                        break

                # Calculate completion date if needed (for done state)
                completion_date = False
                design_price = round(random.uniform(0.5, 1.5), 2)

                # Base values all states will have
                values = {
                    "designer_id": designer.id,
                    "assignment_date": assignment_date,
                    "design_price": design_price,
                    "state": selected_state,
                }

                # Add state-specific data
                if selected_state == "done":
                    # Random number of minutes to complete (between 30 and 240 minutes)
                    minutes_to_complete = random.randint(30, 240)
                    completion_date = assignment_date + timedelta(
                        minutes=minutes_to_complete
                    )
                    values["completion_date"] = completion_date
                    completed_count += 1
                elif selected_state == "processing":
                    processing_count += 1
                elif selected_state == "approving":
                    approving_count += 1

                order.write(values)
                assigned_count += 1

        # Also update some existing assigned orders that aren't completed yet
        existing_assigned = self.search(
            [("designer_id", "!=", False), ("state", "!=", "done")]
        )

        # For existing assignments, distribute across states differently
        existing_state_distribution = {
            "processing": 15,  # 15% chance
            "approving": 25,  # 25% chance
            "done": 60,  # 60% chance to complete existing assignments
        }

        for order in existing_assigned:
            # Determine which state to use based on our distribution
            random_num = random.random() * 100  # 0-100
            cumulative = 0
            selected_state = "all_orders"  # Default fallback

            for state, percentage in existing_state_distribution.items():
                cumulative += percentage
                if random_num <= cumulative:
                    selected_state = state
                    break

            # Use existing assignment date if available
            if order.assignment_date:
                assignment_date = order.assignment_date
            # Otherwise use order date to create assignment date
            elif order.order_date:
                base_date = datetime.combine(order.order_date, datetime.min.time())
                # Add random hours (between 9am-5pm business hours)
                random_hour = random.randint(9, 17)
                random_minute = random.randint(0, 59)
                assignment_date = base_date + timedelta(
                    hours=random_hour, minutes=random_minute
                )
            else:
                # Last resort fallback - use current time
                assignment_date = now

            # Base update values
            update_values = {
                "state": selected_state,
                # Only set assignment date if it wasn't set before
                "assignment_date": order.assignment_date or assignment_date,
            }

            # Add state-specific data
            if selected_state == "done":
                # Random minutes to complete (between 30 and 240 minutes)
                minutes_to_complete = random.randint(30, 240)
                # BUGFIX: Use the assignment date instead of now for completion date calculation
                # This prevents completion dates being set months in the future
                completion_date = (
                    order.assignment_date or assignment_date
                ) + timedelta(minutes=minutes_to_complete)
                update_values["completion_date"] = completion_date
                completed_count += 1
            elif selected_state == "processing":
                processing_count += 1
            elif selected_state == "approving":
                approving_count += 1

            order.write(update_values)

        # Build result message
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Mock Data Generated",
                "message": f"Assigned {assigned_count} new orders across different states:\n"
                f"- {processing_count} in processing\n"
                f"- {approving_count} in approving\n"
                f"- {completed_count} completed",
                "type": "success",
                "sticky": False,
            },
        }
