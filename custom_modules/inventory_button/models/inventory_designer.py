from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import float_round
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class InventoryDesigner(models.Model):
    _name = "inventory.designer"
    _description = "Inventory Designer"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char("Designer Name", required=True, tracking=True)
    email = fields.Char("Email", required=True, tracking=True)
    phone = fields.Char("Phone", tracking=True)
    image_1920 = fields.Image("Profile Picture")
    image_128 = fields.Image(related="image_1920", max_width=128, max_height=128)
    password_input = fields.Char(string="Password", store=False)

    user_id = fields.Many2one("res.users", string="User Account", readonly=True, tracking=True)

    active = fields.Boolean(default=True, tracking=True)
    has_inventory_access = fields.Boolean("Inventory Access", default=True, tracking=True)

    designer_order_ids = fields.One2many('api.product', 'designer_id', string="Assigned Orders")

    assigned_orders_count = fields.Integer(compute="_compute_order_metrics", store=True)
    completed_orders_count = fields.Integer(compute="_compute_order_metrics", store=True)
    avg_turnaround_hours = fields.Float(compute="_compute_order_metrics", store=True)
    completion_rate = fields.Float(compute="_compute_order_metrics", store=True)
    avg_delay_hours = fields.Float(compute="_compute_order_metrics", store=True)
    late_orders_count = fields.Integer(compute="_compute_order_metrics", store=True)
    ongoing_orders_count = fields.Integer(compute="_compute_order_metrics", store=True)
    min_turnaround_hours = fields.Float(compute="_compute_order_metrics", store=True)
    max_turnaround_hours = fields.Float(compute="_compute_order_metrics", store=True)
    active_days_count = fields.Integer(compute="_compute_order_metrics", store=True)
    last_completed_order_date = fields.Date(compute="_compute_order_metrics", store=True)


    MONTH_SELECTION = [
    ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
    ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
    ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ]


    def get_year_selection(self):
        current_year = datetime.today().year
        return [(str(y), str(y)) for y in range(2020, current_year + 1)]

    filter_year = fields.Selection(
        selection=lambda self: self.get_year_selection(),  # Update here
        string="Filter by Year",
        default=lambda self: str(fields.Date.today().year),
        tracking=True
    )

    filter_month = fields.Selection(
        selection=MONTH_SELECTION,
        string="Filter by Month",
        default=lambda self: str(fields.Date.today().month),
        tracking=True
    )

    @api.depends('designer_order_ids', 'filter_year', 'filter_month')
    def _compute_order_metrics(self):
        for rec in self:
            # Convert selected year/month to int
            year = int(rec.filter_year) if rec.filter_year else None
            month = int(rec.filter_month) if rec.filter_month else None
    
            # Filter orders by assignment_date
            filtered_orders = rec.designer_order_ids.filtered(lambda o: (
                (not year or (o.assignment_date and o.assignment_date.year == year)) and
                (not month or (o.assignment_date and o.assignment_date.month == month))
            ))
    
            completed = [o for o in filtered_orders if o.state == 'done']
            ongoing = [o for o in filtered_orders if o.state not in ('done', 'cancel')]
    
            turnaround_times = []
            delays = []
            active_days = set()
            min_tat, max_tat = float('inf'), 0
            last_date = None
            late = 0
    
            for o in completed:
                if o.assignment_date and o.completion_date:
                    tat = (o.completion_date - o.assignment_date).total_seconds() / 3600
                    turnaround_times.append(tat)
                    min_tat = min(min_tat, tat)
                    max_tat = max(max_tat, tat)
    
                if o.completion_date and o.deadline and o.completion_date > o.deadline:
                    delays.append((o.completion_date - o.deadline).total_seconds() / 3600)
                    late += 1
    
                if o.completion_date:
                    last_date = max(last_date or o.completion_date, o.completion_date)
                    active_days.add(o.completion_date.date())
    
            total = len(filtered_orders)
            done = len(completed)
    
            rec.assigned_orders_count = total
            rec.completed_orders_count = done
            rec.avg_turnaround_hours = float_round(sum(turnaround_times) / done, 2) if done else 0
            rec.completion_rate = (done / total) * 100 if total else 0
            rec.avg_delay_hours = float_round(sum(delays) / len(delays), 2) if delays else 0
            rec.late_orders_count = late
            rec.ongoing_orders_count = len(ongoing)
            rec.min_turnaround_hours = float_round(min_tat, 2) if turnaround_times else 0
            rec.max_turnaround_hours = float_round(max_tat, 2) if turnaround_times else 0
            rec.active_days_count = len(active_days)
            rec.last_completed_order_date = last_date

    @api.model
    def create(self, vals):
        password = vals.get("password_input")
        login = vals.get("email")
        phone = vals.get("phone", "")
        image = vals.get("image_1920", False)

        if not password:
            raise ValidationError("Please provide a password for the designer.")
        if not login:
            raise ValidationError("Email is required for the designer.")
        if self.env["res.users"].sudo().search([("login", "=", login)]):
            raise ValidationError(f"Login '{login}' already exists.")

        vals_copy = vals.copy()
        vals_copy.pop("password_input", None)

        designer = super().create(vals_copy)

        groups = [self.env.ref("base.group_user").id]
        if vals.get("has_inventory_access", True):
            groups.append(self.env.ref("stock.group_stock_user").id)
        try:
            groups.append(self.env.ref("inventory_button.group_inventory_designer").id)
        except ValueError:
            _logger.warning("Designer group not found. Ensure it's defined in XML.")

        user = self.env["res.users"].sudo().create({
            "name": designer.name,
            "login": login,
            "email": login,
            "password": password,
            "phone": phone,
            "image_1920": image,
            "groups_id": [(6, 0, groups)],
        })

        if user.partner_id:
            user.partner_id.write({"comment": "Designer User"})
        designer.user_id = user

        return designer

    def toggle_inventory_access(self):
        self.ensure_one()
        inventory_group = self.env.ref("stock.group_stock_user")
        if self.user_id:
            if self.has_inventory_access:
                self.user_id.sudo().write({"groups_id": [(3, inventory_group.id)]})
            else:
                self.user_id.sudo().write({"groups_id": [(4, inventory_group.id)]})
            self.has_inventory_access = not self.has_inventory_access
        return True

    def action_view_assigned_orders(self):
        self.ensure_one()
        return {
            "name": f"Orders Assigned to {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "api.product",
            "view_mode": "kanban,tree,form",
            "domain": [("designer_id", "=", self.id)],
            "context": {"default_designer_id": self.id},
        }

    @api.model
    def generate_mock_designers(self, count=5):
        import random
        first_names = ["Alex", "Taylor", "Jamie", "Skyler", "Casey"]
        last_names = ["Smith", "Brown", "Davis", "White", "Martin"]
        domains = ["gmail.com", "designer.com", "create.io"]
        area_codes = ["201", "202", "212", "213", "310"]
        created = 0
        default_password = "designer123"

        for _ in range(count):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            email = f"{name.lower().replace(' ', '.')}{random.randint(100,999)}@{random.choice(domains)}"
            phone = f"({random.choice(area_codes)}) {random.randint(100,999)}-{random.randint(1000,9999)}"

            if self.env["res.users"].sudo().search([("login", "=", email)]):
                continue

            try:
                self.create({
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "password_input": default_password,
                    "has_inventory_access": True,
                })
                created += 1
            except Exception as e:
                _logger.error(f"Mock creation failed for {name}: {e}")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Mock Designers Created",
                "message": f"{created} designers created. Default password: '{default_password}'",
                "type": "success",
                "sticky": False,
            },
        }
