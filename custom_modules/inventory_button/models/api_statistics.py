from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging
import json
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ApiStatistics(models.Model):
    _name = "inventory.api.statistics"
    _description = "Designer Performance Statistics"
    _auto = False  # This is a database view, not a regular table
    _order = "designer_id, date desc, completed_count desc"

    # Main grouping fields
    designer_id = fields.Many2one(
        "inventory.designer", string="Designer", readonly=True
    )
    date = fields.Date(string="Date", readonly=True)
    source_id = fields.Many2one("res.partner", string="API Source", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)

    # Added computed field for displaying daily products
    api_products = fields.Many2many(
        "api.product",
        string="Designer Products",
        compute="_compute_api_products",
        help="Products that the designer has been working on for this date",
    )

    # Designer performance metrics
    completed_count = fields.Integer(
        string="Completed",
        readonly=True,
        help="Number of designs completed by the designer",
    )
    pending_count = fields.Integer(
        string="Pending",
        readonly=True,
        help="Number of designs pending with the designer",
    )
    quantity = fields.Integer(
        string="Total Products", readonly=True, help="Total number of products assigned"
    )

    # Financial metrics
    earnings = fields.Float(
        string="Designer Earnings",
        readonly=True,
        help="Total earnings for the designer based on completed designs",
    )
    amount = fields.Float(
        string="Order Value", readonly=True, help="Total value of the orders"
    )

    # Time metrics
    avg_completion_time = fields.Float(
        string="Avg. Completion Time (hrs)",
        readonly=True,
        help="Average time in hours to complete a design",
        group_operator="avg",
    )

    # Computed fields
    completion_rate = fields.Float(
        string="Completion Rate (%)", compute="_compute_completion_rate", store=False
    )



    @api.depends("completed_count", "pending_count")
    def _compute_completion_rate(self):
        """Calculate the completion rate as a percentage"""
        for record in self:
            total = record.completed_count + record.pending_count
            if total > 0:
                record.completion_rate = record.completed_count / total
            else:
                record.completion_rate = 0.0

    @api.depends("designer_id", "date")
    def _compute_api_products(self):
        """Compute API products associated with this designer and date"""
        for record in self:
            if record.designer_id and record.date:
                # Search for api.product records matching the designer and date
                record.api_products = self.env["api.product"].search(
                    [
                        ("designer_id", "=", record.designer_id.id),
                        ("date", "=", record.date),
                    ]
                )
            else:
                record.api_products = self.env["api.product"].browse()

    @api.model
    def _select(self):
        """Build the SELECT part of the SQL query"""
        return """
            SELECT
                row_number() OVER () as id,
                api.designer_id as designer_id,
                api.date as date,
                COUNT(CASE WHEN api.state = 'done' THEN 1 ELSE NULL END) as completed_count,
                COUNT(CASE WHEN api.state != 'done' THEN 1 ELSE NULL END) as pending_count,
                SUM(api.quantity) as quantity,
                SUM(CASE WHEN api.state = 'done' THEN api.design_price ELSE 0 END) as earnings,
                SUM(api.order_total) as amount,
                AVG(CASE WHEN api.state = 'done' AND api.turnaround_hours > 0 THEN api.turnaround_hours ELSE NULL END) as avg_completion_time,
                CAST(NULL AS INTEGER) as source_id,
                CAST(NULL AS INTEGER) as product_id
        """

    @api.model
    def _from(self):
        """Build the FROM part of the SQL query"""
        return """
            FROM api_product api
        """

    @api.model
    def _where(self):
        """Build the WHERE part of the SQL query"""
        return """
            WHERE 
                api.designer_id IS NOT NULL
        """

    @api.model
    def _group_by(self):
        """Build the GROUP BY part of the SQL query"""
        return """
            GROUP BY api.designer_id, api.date
        """

    @api.model
    def init(self):
        """Initialize the database view"""
        tools = self.env["ir.model.data"]

        # Drop the view if it exists to avoid column rename issues
        self._cr.execute("DROP VIEW IF EXISTS %s" % self._table)

        # Create the view from scratch
        self._cr.execute(
            """
            CREATE VIEW %s AS (
                %s
                %s
                %s
                %s
            )
        """
            % (
                self._table,
                self._select(),
                self._from(),
                self._where(),
                self._group_by(),
            )
        )

    def name_get(self):
        """Override the default name_get method to provide better record names"""
        result = []
        for record in self:
            if record.designer_id:
                # Format: "Designer Name - April 21, 2025"
                date_str = record.date.strftime("%B %d, %Y") if record.date else ""
                name = f"{record.designer_id.name} - {date_str}"
                result.append((record.id, name))
            else:
                # Fallback if no designer
                result.append((record.id, f"Statistics #{record.id}"))
        return result

    @api.model
    def get_designer_stats(self, designer_id=None, date_from=None, date_to=None):
        """
        Get statistics for one or all designers in a specified time period

        :param designer_id: Optional designer ID to filter results
        :param date_from: Start date for the statistics period
        :param date_to: End date for the statistics period
        :return: Dictionary containing designer statistics
        """
        domain = []

        # Add date range filter if provided
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))

        # Add designer filter if provided
        if designer_id:
            domain.append(("designer_id", "=", designer_id))

        # Get statistics based on the domain
        stats = self.search_read(
            domain,
            [
                "designer_id",
                "completed_count",
                "pending_count",
                "quantity",
                "earnings",
                "amount",
                "avg_completion_time",
            ],
        )

        # Process results for easy consumption
        result = {
            "designers": {},
            "totals": {
                "completed": 0,
                "pending": 0,
                "quantity": 0,
                "earnings": 0,
                "amount": 0,
                "avg_time": 0,
            },
        }

        total_completed = 0
        total_time = 0

        for stat in stats:
            designer = stat.get("designer_id")
            if designer:
                designer_id, designer_name = designer
                if designer_id not in result["designers"]:
                    result["designers"][designer_id] = {
                        "name": designer_name,
                        "completed": 0,
                        "pending": 0,
                        "quantity": 0,
                        "earnings": 0,
                        "amount": 0,
                        "avg_time": 0,
                    }

                # Add stats to designer record
                result["designers"][designer_id]["completed"] += stat["completed_count"]
                result["designers"][designer_id]["pending"] += stat["pending_count"]
                result["designers"][designer_id]["quantity"] += stat["quantity"]
                result["designers"][designer_id]["earnings"] += stat["earnings"]
                result["designers"][designer_id]["amount"] += stat["amount"]

                # Handle avg_completion_time
                if stat["avg_completion_time"]:
                    current_avg = result["designers"][designer_id]["avg_time"]
                    current_completed = result["designers"][designer_id]["completed"]

                    # Calculate weighted average
                    if current_avg > 0:
                        result["designers"][designer_id]["avg_time"] = (
                            (
                                current_avg
                                * (current_completed - stat["completed_count"])
                            )
                            + (stat["avg_completion_time"] * stat["completed_count"])
                        ) / current_completed
                    else:
                        result["designers"][designer_id]["avg_time"] = stat[
                            "avg_completion_time"
                        ]

                # Add to totals
                result["totals"]["completed"] += stat["completed_count"]
                result["totals"]["pending"] += stat["pending_count"]
                result["totals"]["quantity"] += stat["quantity"]
                result["totals"]["earnings"] += stat["earnings"]
                result["totals"]["amount"] += stat["amount"]

                if stat["avg_completion_time"] and stat["completed_count"]:
                    total_time += stat["avg_completion_time"] * stat["completed_count"]
                    total_completed += stat["completed_count"]

        # Calculate overall average completion time
        if total_completed > 0:
            result["totals"]["avg_time"] = total_time / total_completed

        return result

    @api.model
    def get_api_product_stats(self, date_from=None, date_to=None, designer_id=None):
        """
        Get statistics for API products in a specified time period

        :param date_from: Start date for the statistics period
        :param date_to: End date for the statistics period
        :param designer_id: Optional designer ID to filter results
        :return: Dictionary containing API product statistics
        """
        domain = []

        # Add date range filter if provided
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))

        # Add designer filter if provided
        if designer_id:
            domain.append(("designer_id", "=", designer_id))

        # Get raw data from api.product model
        ApiProduct = self.env["api.product"]
        products = ApiProduct.search(domain)

        # Prepare result dictionary
        result = {
            "total_products": len(products),
            "total_value": sum(products.mapped("order_total")),
            "completed_designs": len(products.filtered(lambda p: p.state == "done")),
            "pending_designs": len(products.filtered(lambda p: p.state != "done")),
            "design_earnings": sum(
                p.design_price for p in products if p.state == "done"
            ),
            "avg_completion_time": (
                sum(
                    p.turnaround_hours
                    for p in products
                    if p.state == "done" and p.turnaround_hours > 0
                )
                / len(
                    products.filtered(
                        lambda p: p.state == "done" and p.turnaround_hours > 0
                    )
                )
                if len(
                    products.filtered(
                        lambda p: p.state == "done" and p.turnaround_hours > 0
                    )
                )
                > 0
                else 0
            ),
            "states": {},
        }

        # Count by state
        for state_option in dict(ApiProduct._fields["state"].selection).keys():
            state_count = len(products.filtered(lambda p: p.state == state_option))
            result["states"][state_option] = state_count

        return result

    @api.model
    def refresh_statistics(self):
        """Force refresh the statistics view"""
        self.init()
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
