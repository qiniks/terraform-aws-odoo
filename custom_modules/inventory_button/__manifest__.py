{
    "name": "Orders Management with ShipStation Integration",
    "version": "16.0.1.0.0",
    "category": "Inventory",
    "summary": "Inventory design order management with ShipStation integration",
    "description": """
        Comprehensive inventory design management system integrated with ShipStation.
        Features:
        - Designer assignment and performance tracking
        - Order management and status tracking
        - ShipStation API integration with webhook support
        - Statistical dashboards and reporting
        - Secure API credential management
    """,
    "author": "AIT solutions",
    "depends": ["base", "stock", "web", "mail"],
    "data": [
        "security/inventory_security.xml",
        "security/inventory_designer_security.xml",
        "security/ir.model.access.csv",
        "views/api_product_tree_view.xml",
        "views/api_product_kanban_view.xml",
        "views/api_product_form_view.xml",
        "views/api_product_search_view.xml",
        "views/api_product_actions.xml",
        "views/api_statistics_views.xml",
        "views/mock_data_actions.xml",
        "views/mock_designer_actions.xml",
        "views/shipstation_wizard_view.xml",
        "views/shipstation_views.xml",
        "views/hide_inventory_menus.xml",
        "views/admin_views.xml",
        "views/inventory_designer_views.xml",
        "views/inventory_dashboard_view.xml",
    ],
    "external_dependencies": {
        "python": ["cryptography"],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
