from odoo import models, fields, api, _
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class InventoryDashboard(models.Model):
    _name = "inventory.dashboard"
    _description = "Inventory Statistics Dashboard"

    name = fields.Char(string="Dashboard Name", default="Main Dashboard")
    date_from = fields.Date(
        string="From Date",
        default=lambda self: fields.Date.today() - timedelta(days=30),
    )
    date_to = fields.Date(string="To Date", default=lambda self: fields.Date.today())
    dashboard_active_view = fields.Selection(
        [("products", "Product Statistics"), ("designers", "Designer Statistics")],
        string="Active Dashboard View",
        default="products",
    )
    state_filter = fields.Selection(
        selection="_get_state_options",
        string="State Filter",
        help="Filter orders by state",
    )

    # Dashboard Overview KPIs
    dashboard_total_orders = fields.Integer(
        "Total Orders", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_awaiting_shipment = fields.Integer(
        "Awaiting Shipment", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_completed_orders = fields.Integer(
        "Completed Orders", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_active_designers = fields.Integer(
        "Active Designers", compute="_compute_dashboard_data", compute_sudo=True
    )

    # Revenue summary fields
    dashboard_total_product_revenue = fields.Float(
        "Total Product Revenue", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_total_designer_revenue = fields.Float(
        "Total Designer Revenue", compute="_compute_dashboard_data", compute_sudo=True
    )

    # Order frequency chart data
    dashboard_order_frequency_chart = fields.Text(
        "Order Frequency Chart",
        compute="_compute_dashboard_data",
        store=True,  # Store the field to ensure it's accessible
        compute_sudo=True,
    )

    # Dashboard Product Statistics
    dashboard_product_status_chart = fields.Char(
        "Product Status Chart", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_recent_orders = fields.Html(
        "Recent Orders", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_orders_by_status = fields.Html(
        "Orders By Status", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_product_revenue_table = fields.Html(
        "Product Revenue Breakdown",
        compute="_compute_dashboard_data",
        compute_sudo=True,
    )

    # Dashboard Designer Statistics
    dashboard_designer_performance_chart = fields.Char(
        "Designer Performance Chart",
        compute="_compute_dashboard_data",
        compute_sudo=True,
    )
    dashboard_top_designers = fields.Html(
        "Top Designers", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_designer_stats_table = fields.Html(
        "Designer Stats Table", compute="_compute_dashboard_data", compute_sudo=True
    )
    dashboard_designer_revenue_table = fields.Html(
        "Designer Revenue Analysis",
        compute="_compute_dashboard_data",
        compute_sudo=True,
    )

    # Dashboard Overview KPIs
    dashboard_total_orders = fields.Integer(
        "Total Orders", compute="_compute_dashboard_data"
    )
    dashboard_awaiting_shipment = fields.Integer(
        "Awaiting Shipment", compute="_compute_dashboard_data"
    )
    dashboard_completed_orders = fields.Integer(
        "Completed Orders", compute="_compute_dashboard_data"
    )
    dashboard_active_designers = fields.Integer(
        "Active Designers", compute="_compute_dashboard_data"
    )
    dashboard_total_product_revenue = fields.Float(
        "Total Product Revenue", compute="_compute_dashboard_data"
    )
    dashboard_total_designer_revenue = fields.Float(
        "Total Designer Revenue", compute="_compute_dashboard_data"
    )
    dashboard_order_frequency_chart = fields.Text(
        "Order Frequency Chart", compute="_compute_dashboard_data", store=True
    )
    dashboard_product_status_chart = fields.Char(
        "Product Status Chart", compute="_compute_dashboard_data"
    )
    dashboard_recent_orders = fields.Html(
        "Recent Orders", compute="_compute_dashboard_data"
    )
    dashboard_orders_by_status = fields.Html(
        "Orders By Status", compute="_compute_dashboard_data"
    )
    dashboard_product_revenue_table = fields.Html(
        "Product Revenue Breakdown", compute="_compute_dashboard_data"
    )
    dashboard_designer_performance_chart = fields.Char(
        "Designer Performance Chart", compute="_compute_dashboard_data"
    )
    dashboard_top_designers = fields.Html(
        "Top Designers", compute="_compute_dashboard_data"
    )
    dashboard_designer_stats_table = fields.Html(
        "Designer Stats Table", compute="_compute_dashboard_data"
    )
    dashboard_designer_revenue_table = fields.Html(
        "Designer Revenue Analysis", compute="_compute_dashboard_data"
    )
    dashboard_geographic_stats_table = fields.Html(
        "Geographic Order Statistics", compute="_compute_dashboard_data"
    )

    def _get_state_options(self):
        """Dynamically generate state options based on shipping_address in api.product"""
        products = self.env["api.product"].search([])
        states = set()
        for product in products:
            if product.shipping_address:
                address_lines = product.shipping_address.split("\n")
                for line in address_lines:
                    if "," in line:
                        parts = line.split(",")
                        if len(parts) > 1:
                            state = parts[1].strip()
                            if (
                                state and len(state) <= 2
                            ):  # US state codes are 2 letters
                                states.add(state)
        return [(state, state) for state in sorted(states)]

    @api.depends("dashboard_active_view", "date_from", "date_to", "state_filter")
    def _compute_dashboard_data(self):
        """Compute all dashboard data including geographic statistics"""
        for record in self:
            # Apply date filters
            date_domain = []
            if record.date_from:
                date_domain.append(("date", ">=", record.date_from))
            if record.date_to:
                date_domain.append(("date", "<=", record.date_to))

            # Apply state filter
            if record.state_filter:
                date_domain.append(("shipping_address", "ilike", record.state_filter))

            # Get counts for KPIs
            total_orders = self.env["api.product"].search_count(date_domain)
            awaiting_shipment = self.env["api.product"].search_count(
                date_domain + [("order_status", "=", "awaiting_shipment")]
            )
            completed_orders = self.env["api.product"].search_count(
                date_domain + [("state", "=", "done")]
            )
            active_designers = self.env["inventory.designer"].search_count(
                [("active", "=", True)]
            )

            # Calculate revenue metrics
            products = self.env["api.product"].search(date_domain)
            total_product_revenue = sum(products.mapped("order_total"))
            total_designer_revenue = sum(
                p.design_price for p in products if p.state == "done"
            )

            # Order frequency by day chart
            day_counts = {i: 0 for i in range(7)}
            for product in products:
                if product.date:
                    day_of_week = product.date.weekday()
                    day_counts[day_of_week] += 1
            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            order_frequency_data = [
                {"label": day_names[i], "value": day_counts[i]} for i in range(7)
            ]

            # Product status distribution chart
            status_data = []
            status_counts = {}
            ApiProduct = self.env["api.product"]
            state_selection = dict(ApiProduct._fields["state"].selection)
            for status in ["all_orders", "processing", "approving", "done"]:
                count = self.env["api.product"].search_count(
                    date_domain + [("state", "=", status)]
                )
                status_counts[status] = count
                status_data.append(
                    {"label": state_selection.get(status, status), "value": count}
                )

            # Designer performance chart
            designers = self.env["inventory.designer"].search(
                [("active", "=", True)], limit=10
            )
            designer_data = []
            designer_revenue_data = {}
            for designer in designers:
                assigned_count = self.env["api.product"].search_count(
                    date_domain + [("designer_id", "=", designer.id)]
                )
                completed_count = self.env["api.product"].search_count(
                    date_domain
                    + [("designer_id", "=", designer.id), ("state", "=", "done")]
                )
                completed_with_times = self.env["api.product"].search(
                    date_domain
                    + [
                        ("designer_id", "=", designer.id),
                        ("state", "=", "done"),
                        ("turnaround_hours", ">", 0),
                    ]
                )
                avg_turnaround = 0
                if completed_with_times:
                    avg_turnaround = sum(
                        order.turnaround_hours for order in completed_with_times
                    ) / len(completed_with_times)
                designer_revenue = sum(
                    order.design_price for order in completed_with_times
                )
                designer_revenue_data[designer.id] = {
                    "name": designer.name,
                    "revenue": designer_revenue,
                    "count": len(completed_with_times),
                }
                designer_data.append(
                    {
                        "label": designer.name,
                        "value": completed_count,
                        "assigned": assigned_count,
                        "completed": completed_count,
                        "avg_turnaround": round(avg_turnaround, 2),
                        "revenue": designer_revenue,
                    }
                )
            designer_data = sorted(
                designer_data, key=lambda x: x["completed"], reverse=True
            )

            # Recent orders table
            recent_orders_html = '<table class="table table-sm table-striped"><thead><tr><th>Order #</th><th>Name</th><th>Date</th><th>Status</th></tr></thead><tbody>'
            recent_orders = self.env["api.product"].search(
                date_domain, order="date desc, create_date desc", limit=10
            )
            for order in recent_orders:
                status_class = "secondary"
                if order.state == "done":
                    status_class = "success"
                elif order.state == "approving":
                    status_class = "warning"
                elif order.state == "processing":
                    status_class = "primary"
                recent_orders_html += f"""
                    <tr>
                        <td>{order.order_number or ''}</td>
                        <td>{order.name or ''}</td>
                        <td>{order.date.strftime('%Y-%m-%d') if order.date else ''}</td>
                        <td><span class="badge badge-{status_class}">{state_selection.get(order.state, order.state)}</span></td>
                    </tr>
                """
            recent_orders_html += "</tbody></table>"

            # Orders by status table
            orders_by_status_html = """
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Count</th>
                            <th>Percentage</th>
                            <th>Visual</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for status in ["all_orders", "processing", "approving", "done"]:
                count = status_counts.get(status, 0)
                percentage = (count / total_orders * 100) if total_orders > 0 else 0
                bar_class = (
                    "bg-success"
                    if status == "done"
                    else (
                        "bg-info"
                        if status == "approving"
                        else "bg-primary" if status == "processing" else "bg-danger"
                    )
                )
                orders_by_status_html += f"""
                    <tr>
                        <td>{state_selection.get(status, status)}</td>
                        <td>{count}</td>
                        <td>{percentage:.1f}%</td>
                        <td>
                            <div class="progress">
                                <div class="progress-bar {bar_class}" role="progressbar" style="width: {percentage}%"></div>
                            </div>
                        </td>
                    </tr>
                """
            orders_by_status_html += "</tbody></table>"

            # Geographic order statistics table
            geographic_stats_html = """
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            <th>Country</th>
                            <th>State</th>
                            <th>Quantity</th>
                            <th>Percentage</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            geographic_metrics = {}
            total_quantity = 0
            for product in products:
                if product.shipping_address or product.item_details:
                    # Initialize country and state
                    country = state = ""

                    # Parse shipping_address for state and country
                    if product.shipping_address:
                        address_lines = product.shipping_address.split("\n")
                        for line in address_lines:
                            if "," in line:
                                parts = line.split(",")
                                if len(parts) > 1:
                                    state = parts[1].strip()
                            if "US" in line.upper():
                                country = "USA"

                    # Fallback to item_details for country and state
                    if product.item_details:
                        try:
                            # Parse item_details if it's a JSON string
                            item_details = (
                                json.loads(product.item_details)
                                if isinstance(product.item_details, str)
                                else product.item_details
                            )
                            # Check if item_details is a dict (full order) and has shipTo
                            if isinstance(item_details, dict):
                                ship_to = item_details.get("shipTo", {})
                                if not country:
                                    country = ship_to.get("country", "Unknown")
                                if not state:
                                    state = ship_to.get("state", "N/A")
                            else:
                                _logger.warning(
                                    f"Unexpected item_details format for product {product.id}: {type(item_details)}"
                                )
                                country = country or "Unknown"
                                state = state or "N/A"
                        except (json.JSONDecodeError, TypeError) as e:
                            _logger.warning(
                                f"Failed to parse item_details for product {product.id}: {e}"
                            )
                            country = country or "Unknown"
                            state = state or "N/A"

                    # Default if no data
                    if not country:
                        country = "Unknown"
                    if not state:
                        state = "N/A"

                    # Aggregate quantities
                    key = (country, state)
                    if key not in geographic_metrics:
                        geographic_metrics[key] = 0
                    geographic_metrics[key] += product.quantity or 0
                    total_quantity += product.quantity or 0

            for (country, state), quantity in sorted(
                geographic_metrics.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (
                    (quantity / total_quantity * 100) if total_quantity > 0 else 0
                )
                geographic_stats_html += f"""
                    <tr>
                        <td>{country}</td>
                        <td>{state}</td>
                        <td>{quantity}</td>
                        <td>{percentage:.1f}%</td>
                    </tr>
                """
            geographic_stats_html += "</tbody></table>"

            # Top designers table
            top_designers_html = '<table class="table table-sm table-striped"><thead><tr><th>Designer</th><th>Completed</th><th>Success Rate</th><th>Revenue</th></tr></thead><tbody>'
            for designer_stat in designer_data[:5]:
                success_rate = (
                    (designer_stat["completed"] / designer_stat["assigned"] * 100)
                    if designer_stat["assigned"] > 0
                    else 0
                )
                top_designers_html += f"""
                    <tr>
                        <td>{designer_stat['label']}</td>
                        <td>{designer_stat['completed']}</td>
                        <td>{success_rate:.1f}%</td>
                        <td>${designer_stat['revenue']:.2f}</td>
                    </tr>
                """
            top_designers_html += "</tbody></table>"

            # Detailed designer stats table
            designer_stats_html = """
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            <th>Designer</th>
                            <th>Assigned Orders</th>
                            <th>Completed Orders</th>
                            <th>Completion Rate</th>
                            <th>Avg Turnaround (Hours)</th>
                            <th>Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for designer_stat in designer_data:
                completion_rate = (
                    (designer_stat["completed"] / designer_stat["assigned"] * 100)
                    if designer_stat["assigned"] > 0
                    else 0
                )
                designer_stats_html += f"""
                    <tr>
                        <td>{designer_stat['label']}</td>
                        <td>{designer_stat['assigned']}</td>
                        <td>{designer_stat['completed']}</td>
                        <td>{completion_rate:.1f}%</td>
                        <td>{designer_stat['avg_turnaround']}</td>
                        <td>${designer_stat['revenue']:.2f}</td>
                    </tr>
                """
            designer_stats_html += "</tbody></table>"

            # Product revenue breakdown
            product_revenue_html = """
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Units Sold</th>
                            <th>Total Revenue</th>
                            <th>Average Price</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            product_metrics = {}
            for product in products:
                product_name = product.product_name or product.name
                if product_name not in product_metrics:
                    product_metrics[product_name] = {"count": 0, "revenue": 0}
                product_metrics[product_name]["count"] += 1
                product_metrics[product_name]["revenue"] += product.order_total or 0
            sorted_products = sorted(
                product_metrics.items(), key=lambda x: x[1]["revenue"], reverse=True
            )
            for product_name, metrics in sorted_products[:10]:
                avg_price = (
                    metrics["revenue"] / metrics["count"] if metrics["count"] > 0 else 0
                )
                product_revenue_html += f"""
                    <tr>
                        <td>{product_name}</td>
                        <td>{metrics['count']}</td>
                        <td>${metrics['revenue']:.2f}</td>
                        <td>${avg_price:.2f}</td>
                    </tr>
                """
            product_revenue_html += "</tbody></table>"

            # Designer revenue analysis
            designer_revenue_html = """
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            <th>Designer</th>
                            <th>Completed Orders</th>
                            <th>Total Revenue</th>
                            <th>Average Per Order</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            sorted_designers = sorted(
                designer_revenue_data.values(), key=lambda x: x["revenue"], reverse=True
            )
            for designer in sorted_designers:
                avg_revenue = (
                    designer["revenue"] / designer["count"]
                    if designer["count"] > 0
                    else 0
                )
                designer_revenue_html += f"""
                    <tr>
                        <td>{designer['name']}</td>
                        <td>{designer['count']}</td>
                        <td>${designer['revenue']:.2f}</td>
                        <td>${avg_revenue:.2f}</td>
                    </tr>
                """
            designer_revenue_html += "</tbody></table>"

            # Set computed values
            record.dashboard_total_orders = total_orders
            record.dashboard_awaiting_shipment = awaiting_shipment
            record.dashboard_completed_orders = completed_orders
            record.dashboard_active_designers = active_designers
            record.dashboard_total_product_revenue = total_product_revenue
            record.dashboard_total_designer_revenue = total_designer_revenue
            record.dashboard_product_status_chart = json.dumps(
                {
                    "type": "pie",
                    "data": status_data,
                    "graph_type": "pie",
                    "background_color": "#875A7B",
                    "title": "Order Status Distribution",
                }
            )
            record.dashboard_recent_orders = recent_orders_html
            record.dashboard_orders_by_status = orders_by_status_html
            record.dashboard_product_revenue_table = product_revenue_html
            record.dashboard_order_frequency_chart = json.dumps(
                {
                    "type": "bar",
                    "data": order_frequency_data,
                    "graph_type": "bar",
                    "background_color": "#5B9BD5",
                    "title": "Orders by Day of Week",
                    "stacked": False,
                }
            )
            record.dashboard_designer_performance_chart = json.dumps(
                {
                    "type": "bar",
                    "data": designer_data,
                    "graph_type": "bar",
                    "background_color": "#00A09D",
                    "measure": "completed",
                    "title": "Completed Orders by Designer",
                }
            )
            record.dashboard_top_designers = top_designers_html
            record.dashboard_designer_stats_table = designer_stats_html
            record.dashboard_designer_revenue_table = designer_revenue_html
            record.dashboard_geographic_stats_table = geographic_stats_html

    def action_apply_date_filter(self):
        """Apply the selected date range and state filter"""
        self.ensure_one()
        self._compute_dashboard_data()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Filter Applied"),
                "message": _("Dashboard data updated with selected filters"),
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_reset_date_filter(self):
        """Reset date and state filters to default"""
        self.ensure_one()
        today = fields.Date.today()
        self.write(
            {
                "date_from": today - timedelta(days=30),
                "date_to": today,
                "state_filter": False,
            }
        )
        self._compute_dashboard_data()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Filters Reset"),
                "message": _("Filters reset to default"),
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_view_product_stats(self):
        """Switch to product statistics view"""
        self.ensure_one()
        self.write({"dashboard_active_view": "products"})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("View Changed"),
                "message": _("Showing Product Statistics"),
                "sticky": False,
                "type": "info",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_view_designer_stats(self):
        """Switch to designer statistics view"""
        self.ensure_one()
        self.write({"dashboard_active_view": "designers"})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("View Changed"),
                "message": _("Showing Designer Statistics"),
                "sticky": False,
                "type": "info",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    @api.model
    def get_dashboard_record(self):
        """Get or create a single persistent dashboard record"""
        dashboard = self.search([], limit=1)
        if not dashboard:
            dashboard = self.create({"name": "Main Dashboard"})
        return dashboard
