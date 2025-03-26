{
    "name": "CRM Hawk Tuah Button",
    "version": "1.0",
    "category": "Sales/CRM",
    "summary": "Add Hawk Tuah button to CRM",
    "description": """
        This module adds a Hawk Tuah button next to the New button in CRM.
    """,
    "author": "Odoocker",
    "website": "https://odoocker.com",
    "depends": ["crm", "web"],
    "data": [
        "views/crm_lead_views.xml",
    ],
    # "assets": {
    #     "web.assets_backend": [
    #         "/crm_field_rename/static/src/js/hawk_button.js",
    #     ],
    # },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
