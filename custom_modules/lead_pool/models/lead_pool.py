# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CRMLead(models.Model):
    _inherit = "crm.lead"

    is_pool_lead = fields.Boolean(string="Is Pool Lead", default=True, tracking=True)
    original_email = fields.Char(
        string="Original Email", groups="lead_pool.group_org_admin"
    )
    original_phone = fields.Char(
        string="Original Phone", groups="lead_pool.group_org_admin"
    )
    obfuscated_email = fields.Char(
        string="Contact Email", compute="_compute_obfuscated_contact"
    )
    obfuscated_phone = fields.Char(
        string="Contact Phone", compute="_compute_obfuscated_contact"
    )
    benefits = fields.Text(
        string="Benefits",
        help="List of benefits or value proposition for claiming this lead",
    )
    bermuda_transaction_id = fields.Char(
        string="Bermuda Transaction ID",
        readonly=True,
        help="Transaction ID from Bermuda Rater API",
    )

    @api.depends("email_from", "phone", "is_pool_lead", "user_id")
    def _compute_obfuscated_contact(self):
        for lead in self:
            if lead.is_pool_lead and not lead.user_id:
                # Obfuscate email
                if lead.email_from:
                    parts = lead.email_from.split("@")
                    if len(parts) == 2:
                        username = parts[0]
                        domain = parts[1]
                        obfuscated_username = username[:2] + "*" * (len(username) - 2)
                        lead.obfuscated_email = f"{obfuscated_username}@{domain}"
                    else:
                        lead.obfuscated_email = False
                else:
                    lead.obfuscated_email = False

                # Obfuscate phone
                if lead.phone:
                    if len(lead.phone) > 4:
                        lead.obfuscated_phone = (
                            "*" * (len(lead.phone) - 4) + lead.phone[-4:]
                        )
                    else:
                        lead.obfuscated_phone = lead.phone
                else:
                    lead.obfuscated_phone = False
            else:
                lead.obfuscated_email = lead.email_from
                lead.obfuscated_phone = lead.phone

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_pool_lead", True):
                # Store original contact info
                vals["original_email"] = vals.get("email_from")
                vals["original_phone"] = vals.get("phone")
        return super(CRMLead, self).create(vals_list)

    def claim_lead(self):
        """Claim a lead from the pool for the current user/company"""
        self.ensure_one()

        if not self.is_pool_lead:
            raise UserError(_("This lead has already been claimed."))

        if self.user_id:
            raise UserError(
                _("This lead is already assigned to %s.") % self.user_id.name
            )

        # Call Bermuda Rater API
        api_result = self.env["bermuda.rater.api"].call_open_transaction(self)

        # Find the first stage for leads in the CRM pipeline
        first_stage = self.env["crm.stage"].search(
            [("team_id", "=", False)], order="sequence", limit=1
        )
        if not first_stage:
            first_stage = self.env["crm.stage"].search([], order="sequence", limit=1)

        update_vals = {
            "is_pool_lead": False,
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
            "email_from": self.original_email,
            "phone": self.original_phone,
            "type": "lead",  # Ensure it's a lead type
        }

        # Assign to first stage if found
        if first_stage:
            update_vals["stage_id"] = first_stage.id

        # Add transaction ID if API call was successful
        if api_result.get("success"):
            update_vals["bermuda_transaction_id"] = api_result.get("transaction_id")

        # Update lead
        self.write(update_vals)

        # Return notification or redirect
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Lead Claimed"),
                "message": api_result.get("message", _("Lead successfully claimed.")),
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window_close",
                },
            },
        }

    def convert_to_opportunity(self):
        """Convert a lead to an opportunity and move it to the pipeline"""
        self.ensure_one()

        if self.type == "opportunity":
            raise UserError(_("This lead is already an opportunity."))

        # Get opportunity stage (usually the first in pipeline)
        first_opp_stage = self.env["crm.stage"].search(
            [("team_id", "=", False), ("is_won", "=", False)], order="sequence", limit=1
        )
        if not first_opp_stage:
            first_opp_stage = self.env["crm.stage"].search(
                [("is_won", "=", False)], order="sequence", limit=1
            )

        # Convert to opportunity
        self.write(
            {
                "type": "opportunity",
                "stage_id": first_opp_stage.id if first_opp_stage else False,
            }
        )

        # Return a redirect to the opportunity form view
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }


class LeadPool(models.Model):
    _name = "lead.pool"
    _description = "Lead Pool"

    name = fields.Char(string="Name", required=True)
    company_name = fields.Char(string="Company")
    description = fields.Text(string="Description")

    # Sensitive information - restricted visibility
    email = fields.Char(string="Email", groups="lead_pool.group_org_admin")
    phone = fields.Char(string="Phone", groups="lead_pool.group_org_admin")

    # Organization field to restrict by organization
    organization_id = fields.Many2one(
        "res.company", string="Organization", default=lambda self: self.env.company.id
    )

    # Status field to track lead state
    state = fields.Selection(
        [
            ("available", "Available"),
            ("assigned", "Assigned"),
        ],
        default="available",
        string="Status",
    )

    assigned_user_id = fields.Many2one("res.users", string="Assigned To")

    @api.model
    def create(self, vals):
        """Override create to ensure organization is set"""
        if not vals.get("organization_id"):
            vals["organization_id"] = self.env.company.id
        return super(LeadPool, self).create(vals)

    def assign_lead(self):
        """Assign the lead to the current user and move it to CRM pipeline"""
        self.ensure_one()

        if self.state != "available":
            raise UserError(_("This lead is already assigned."))

        current_user = self.env.user

        # Create a new CRM lead based on pool lead
        crm_lead = self.env["crm.lead"].create(
            {
                "name": self.name,
                "partner_name": self.company_name,
                "description": self.description,
                "email_from": self.email,
                "phone": self.phone,
                "user_id": current_user.id,
                "company_id": self.organization_id.id,
                "is_pool_lead": True,
                "original_email": self.email,
                "original_phone": self.phone,
            }
        )

        # Update the pool lead status
        self.write({"state": "assigned", "assigned_user_id": current_user.id})

        # Delete this lead from the pool after assignment
        self.unlink()

        return {
            "type": "ir.actions.act_window",
            "name": _("Assigned Lead"),
            "res_model": "crm.lead",
            "res_id": crm_lead.id,
            "view_mode": "form",
            "target": "current",
        }
