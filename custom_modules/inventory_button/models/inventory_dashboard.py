from odoo import models, fields, api, _
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class InventoryDashboard(models.Model):
    _name = "inventory.dashboard"
    _description = "Inventory Statistics Dashboard"

    # We don't need any required fields in this model as it's just for the dashboard
    name = fields.Char(string="Dashboard Name", default="Main Dashboard")

    # Date range fields for filtering dashboard data
    date_from = fields.Date(
        string="From Date",
        default=lambda self: fields.Date.today() - timedelta(days=30),
    )
    date_to = fields.Date(string="To Date", default=lambda self: fields.Date.today())

    # Dashboard view toggle
    dashboard_active_view = fields.Selection(
        [("products", "Product Statistics"), ("designers", "Designer Statistics")],
        string="Active Dashboard View",
        default="products",
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

    # Revenue summary fields
    dashboard_total_product_revenue = fields.Float(
        "Total Product Revenue", compute="_compute_dashboard_data"
    )
    dashboard_total_designer_revenue = fields.Float(
        "Total Designer Revenue", compute="_compute_dashboard_data"
    )

    # Order frequency chart data
    dashboard_order_frequency_chart = fields.Char(
        "Order Frequency Chart", compute="_compute_dashboard_data"
    )

    # Dashboard Product Statistics
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

    # Dashboard Designer Statistics
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

    @api.depends("dashboard_active_view", "date_from", "date_to")
    def _compute_dashboard_data(self):
        """Compute all dashboard data at once for efficiency"""
        for record in self:
            # Apply date filters if provided
            date_domain = []
            if record.date_from:
                date_domain.append(("date", ">=", record.date_from))
            if record.date_to:
                date_domain.append(("date", "<=", record.date_to))

            # Get counts for KPIs with date filter applied
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

            # Data for order frequency by day chart
            day_counts = {}
            for i in range(7):
                day_counts[i] = 0

            for product in products:
                if product.date:
                    # Get day of week (0=Monday, 6=Sunday)
                    day_of_week = product.date.weekday()
                    day_counts[day_of_week] += 1

            # Convert to chart data format
            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            order_frequency_data = []
            for i in range(7):
                order_frequency_data.append(
                    {"label": day_names[i], "value": day_counts[i]}
                )

            # Data for product status distribution chart
            status_data = []
            status_counts = {}

            # Get the selection field definition from api.product model
            ApiProduct = self.env["api.product"]
            state_selection = dict(ApiProduct._fields["state"].selection)

            for status in ["all_products", "processing", "approving", "done"]:
                count = self.env["api.product"].search_count(
                    date_domain + [("state", "=", status)]
                )
                status_counts[status] = count
                status_data.append(
                    {
                        "label": state_selection.get(status, status),
                        "value": count,
                    }
                )

            # Data for designer performance chart
            designers = self.env["inventory.designer"].search(
                [("active", "=", True)], limit=10
            )
            designer_data = []
            designer_revenue_data = {}

            for designer in designers:
                # Get assigned count with date filter
                assigned_count = self.env["api.product"].search_count(
                    date_domain + [("designer_id", "=", designer.id)]
                )
                # Get completed count with date filter
                completed_count = self.env["api.product"].search_count(
                    date_domain
                    + [("designer_id", "=", designer.id), ("state", "=", "done")]
                )
                # Calculate average turnaround time
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

                # Calculate designer revenue
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

            # Sort designer data by completed orders (highest first)
            designer_data = sorted(
                designer_data, key=lambda x: x["completed"], reverse=True
            )

            # Generate HTML for recent orders table
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

            # Generate HTML for orders by status table
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
            for status in ["all_products", "processing", "approving", "done"]:
                count = status_counts.get(status, 0)
                percentage = 0
                if total_orders > 0:
                    percentage = (count / total_orders) * 100

                # Determine color based on status
                if status == "done":
                    bar_class = "bg-success"
                elif status == "approving":
                    bar_class = "bg-info"
                elif status == "processing":
                    bar_class = "bg-primary"
                else:
                    bar_class = "bg-danger"

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

            # Generate HTML for top designers
            top_designers_html = '<table class="table table-sm table-striped"><thead><tr><th>Designer</th><th>Completed</th><th>Success Rate</th><th>Revenue</th></tr></thead><tbody>'
            for designer_stat in designer_data[:5]:  # Top 5 designers
                success_rate = 0
                if designer_stat["assigned"] > 0:
                    success_rate = (
                        designer_stat["completed"] / designer_stat["assigned"]
                    ) * 100

                top_designers_html += f"""
                    <tr>
                        <td>{designer_stat['label']}</td>
                        <td>{designer_stat['completed']}</td>
                        <td>{success_rate:.1f}%</td>
                        <td>${designer_stat['revenue']:.2f}</td>
                    </tr>
                """
            top_designers_html += "</tbody></table>"

            # Generate HTML for detailed designer stats
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
                completion_rate = 0
                if designer_stat["assigned"] > 0:
                    completion_rate = (
                        designer_stat["completed"] / designer_stat["assigned"]
                    ) * 100

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

            # Generate HTML for product revenue breakdown
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

            # Group products by name and calculate revenue metrics
            product_metrics = {}
            for product in products:
                product_name = product.product_name or product.name
                if product_name not in product_metrics:
                    product_metrics[product_name] = {
                        "count": 0,
                        "revenue": 0,
                    }

                product_metrics[product_name]["count"] += 1
                product_metrics[product_name]["revenue"] += product.order_total or 0

            # Sort products by total revenue
            sorted_products = sorted(
                product_metrics.items(), key=lambda x: x[1]["revenue"], reverse=True
            )

            for product_name, metrics in sorted_products[:10]:  # Top 10 products
                avg_price = 0
                if metrics["count"] > 0:
                    avg_price = metrics["revenue"] / metrics["count"]

                product_revenue_html += f"""
                    <tr>
                        <td>{product_name}</td>
                        <td>{metrics['count']}</td>
                        <td>${metrics['revenue']:.2f}</td>
                        <td>${avg_price:.2f}</td>
                    </tr>
                """
            product_revenue_html += "</tbody></table>"

            # Generate HTML for designer revenue analysis
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

            # Sort designers by revenue
            sorted_designers = sorted(
                designer_revenue_data.values(), key=lambda x: x["revenue"], reverse=True
            )

            for designer in sorted_designers:
                avg_revenue = 0
                if designer["count"] > 0:
                    avg_revenue = designer["revenue"] / designer["count"]

                designer_revenue_html += f"""
                    <tr>
                        <td>{designer['name']}</td>
                        <td>{designer['count']}</td>
                        <td>${designer['revenue']:.2f}</td>
                        <td>${avg_revenue:.2f}</td>
                    </tr>
                """
            designer_revenue_html += "</tbody></table>"

            # Set all computed values for the record
            record.dashboard_total_orders = total_orders
            record.dashboard_awaiting_shipment = awaiting_shipment
            record.dashboard_completed_orders = completed_orders
            record.dashboard_active_designers = active_designers
            record.dashboard_total_product_revenue = total_product_revenue
            record.dashboard_total_designer_revenue = total_designer_revenue

            # Set product stats
            record.dashboard_product_status_chart = json.dumps(
                {
                    "type": "pie",
                    "data": status_data,
                    "graph_type": "pie",  # Add this explicitly for the widget
                    "background_color": "#875A7B",  # Odoo's default purple
                    "title": "Order Status Distribution",
                }
            )
            record.dashboard_recent_orders = recent_orders_html
            record.dashboard_orders_by_status = orders_by_status_html
            record.dashboard_product_revenue_table = product_revenue_html

            # Set order frequency chart
            record.dashboard_order_frequency_chart = json.dumps(
                {
                    "type": "bar",
                    "data": order_frequency_data,
                    "graph_type": "bar",  # Add this explicitly for the widget
                    "background_color": "#5B9BD5",  # Blue color
                    "title": "Orders by Day of Week",
                    "stacked": False,
                }
            )

            # Set designer stats
            record.dashboard_designer_performance_chart = json.dumps(
                {
                    "type": "bar",
                    "data": designer_data,
                    "graph_type": "bar",  # Add this explicitly for the widget
                    "background_color": "#00A09D",  # Teal color
                    "measure": "completed",
                    "title": "Completed Orders by Designer",
                }
            )
            record.dashboard_top_designers = top_designers_html
            record.dashboard_designer_stats_table = designer_stats_html
            record.dashboard_designer_revenue_table = designer_revenue_html

    def action_apply_date_filter(self):
        """Apply the selected date range to filter dashboard statistics"""
        self.ensure_one()

        # Just trigger recomputation - no need to modify the record
        self._compute_dashboard_data()

        # Return client action that maintains the form state without reloading
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Filter Applied"),
                "message": _("Dashboard data updated with selected date range"),
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_reset_date_filter(self):
        """Reset date filters to default (last 30 days)"""
        self.ensure_one()

        # Update date fields to default values
        today = fields.Date.today()
        self.write(
            {
                "date_from": today - timedelta(days=30),
                "date_to": today,
            }
        )

        # Trigger recomputation to refresh the dashboard
        self._compute_dashboard_data()

        # Return client action that maintains the form state without reloading
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Filters Reset"),
                "message": _("Date range has been reset to default (last 30 days)"),
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_view_product_stats(self):
        """Switch the dashboard to product statistics view"""
        self.ensure_one()
        self.write({"dashboard_active_view": "products"})

        # Return notification action to avoid page reload
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
        """Switch the dashboard to designer statistics view"""
        self.ensure_one()
        self.write({"dashboard_active_view": "designers"})

        # Return notification action to avoid page reload
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
