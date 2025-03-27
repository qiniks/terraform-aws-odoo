# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bermuda_api_url = fields.Char(
        string="Bermuda Rater API URL",
        config_parameter="bermuda_rater.api_url",
        default="https://api.bermudarater.example.com/open-transaction",
    )

    bermuda_api_key = fields.Char(
        string="Bermuda Rater API Key", config_parameter="bermuda_rater.api_key"
    )
