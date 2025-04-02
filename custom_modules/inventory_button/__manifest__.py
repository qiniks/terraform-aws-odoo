{
    "name": "Inventory Header Button",
    "version": "16.0.1.0.0",
    "category": "Inventory",
    "summary": "Adds a custom button to the inventory header",
    "author": "Your Name",
    "depends": ["base", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_views.xml",
        "views/api_product_views.xml",
    ],
    "installable": True,
    "application": True,
}
