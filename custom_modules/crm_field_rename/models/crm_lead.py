from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # All code related to "generate happiness" has been removed

    def action_hawk_tuah(self):
        # This action will be triggered when the Hawk Tuah button is clicked
        # You can define what you want it to do here
        return {
            "type": "ir.actions.act_window",
            "name": "Hawk Tuah Action",
            "res_model": "crm.lead",
            "view_mode": "form,kanban,tree",
            "target": "current",
        }

    def hawk_tuah_action(self):
        """
        This action will be triggered when the Hawk Tuah button is clicked
        """
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Hawk Tuah",
                "message": "Hawk Tuah button was clicked!",
                "sticky": False,
                "type": "success",
            },
        }
