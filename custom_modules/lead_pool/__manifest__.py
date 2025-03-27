# -*- coding: utf-8 -*-
{
    "name": "Lead Pool Management",
    "version": "1.0",
    "category": "Sales/CRM",
    "summary": "Manage a shared pool of leads within organizations",
    "description": """
Lead Pool Management
===================
This module allows organizations to manage a shared pool of leads.
- Org users can see leads but not sensitive details
- Leads can be assigned to users, moving them out of the pool
- Organization-based security rules
- Integration with Bermuda Rater API for quote generation
""",
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": ["base", "crm"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/lead_pool_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
