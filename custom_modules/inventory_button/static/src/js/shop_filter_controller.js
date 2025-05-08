odoo.define('inventory_button.ShopFilterController', function (require) {
    "use strict";

    const { registry } = require('@web/core/registry');
    const { Component, useState, onWillStart } = owl;
    const { Dropdown } = require('@web/core/dropdown/dropdown');
    const { DropdownItem } = require('@web/core/dropdown/dropdown_item');
    const { useService } = require('@web/core/utils/hooks');

    /**
     * Shop Filter Menu Component
     *
     * This component displays a dropdown menu with all available shops/stores
     * and allows filtering products by the selected shop.
     */
    class ShopFilterMenu extends Component {
        static template = 'inventory_button.ShopFilterMenu';
        static components = { Dropdown, DropdownItem };
        static props = {};
        
        setup() {
            this.orm = useService('orm');
            this.action = useService("action");
            this.notification = useService("notification");
            
            this.state = useState({
                shops: [],
                searchValue: "",
                isLoaded: false,
                selectionChanged: false,
                isApplying: false
            });
            
            onWillStart(async () => {
                await this.loadShops();
            });
        }
        
        async loadShops() {
            try {
                // Use the ORM service to call the backend method
                const shops = await this.orm.call(
                    'api.product',
                    'get_all_shops',
                    []
                );
                
                if (shops && Array.isArray(shops)) {
                    this.state.shops = shops.map(shop => ({
                        id: shop.store_id,
                        name: shop.store_name || `Store ${shop.store_id}`,
                        color: shop.store_color || '#CCCCCC',
                        selected: false
                    }));
                } else {
                    console.warn("No shops returned from server or invalid format");
                    this.state.shops = [];
                }
                
                this.state.isLoaded = true;
            } catch (error) {
                console.error('Failed to load shops:', error);
                this.state.shops = [];
                this.state.isLoaded = true;
            }
        }
        
        get displayedShops() {
            if (!this.state.shops || !this.state.shops.length) {
                return [];
            }
            
            if (this.state.searchValue) {
                return this.state.shops.filter(shop => 
                    shop.name.toLowerCase().includes(this.state.searchValue.toLowerCase())
                );
            }
            return this.state.shops;
        }
        
        get hasSelectedShops() {
            return this.state.shops && this.state.shops.some(shop => shop.selected);
        }
        
        get selectedCount() {
            if (!this.state.shops) return 0;
            return this.state.shops.filter(shop => shop.selected).length;
        }
        
        // Toggle shop selection without applying filter immediately
        toggleShop(shopId) {
            // Find the shop in the state
            const shopIndex = this.state.shops.findIndex(shop => shop.id === shopId);
            if (shopIndex >= 0) {
                // Create a copy of the shops array
                const updatedShops = [...this.state.shops];
                // Toggle the selected state
                updatedShops[shopIndex].selected = !updatedShops[shopIndex].selected;
                // Update the state with the new array
                this.state.shops = updatedShops;
                // Mark that selection has changed
                this.state.selectionChanged = true;
            }
        }
        
        clearAll() {
            if (!this.state.shops) return;
            
            // Update all shops to be unselected
            this.state.shops = this.state.shops.map(shop => ({
                ...shop,
                selected: false
            }));
            
            // Mark that selection has changed
            this.state.selectionChanged = true;
        }
        
        selectAll() {
            if (!this.state.shops) return;
            
            // Update all shops to be selected
            this.state.shops = this.state.shops.map(shop => ({
                ...shop,
                selected: true
            }));
            
            // Mark that selection has changed
            this.state.selectionChanged = true;
        }
        
        updateSearchValue(ev) {
            this.state.searchValue = ev.target.value || '';
        }
        
        // Apply filter button - fixed implementation
        async applyFilter() {
            if (!this.state.shops || this.state.isApplying) return;
            
            try {
                // Set flag to prevent double-clicks
                this.state.isApplying = true;
                
                // Reset the selection changed flag
                this.state.selectionChanged = false;
                
                // Get all selected shops
                const selectedShops = this.state.shops.filter(shop => shop.selected);
                
                let domain = [];
                
                // Build domain filter for selected shops
                if (selectedShops.length > 0) {
                    const shopIds = selectedShops.map(shop => shop.id);
                    domain = [['store_id', 'in', shopIds]];
                }
                
                // Get current view type (list vs kanban)
                const currentURL = window.location.href;
                const viewType = currentURL.includes('view_type=list') ? 'list' : 'kanban';
                
                console.log("Applying shop filter with domain:", domain);
                
                // Use doAction to reload the current view with the new domain
                await this.action.doAction({
                    type: 'ir.actions.act_window',
                    name: 'API Orders',
                    res_model: 'api.product',
                    views: [[false, viewType]],
                    target: 'current',
                    domain: domain,
                    flags: {
                        clearBreadcrumbs: true,
                        preventBreadcrumb: true
                    }
                });
                
                // If we get here, the filter was applied successfully
                this.state.isApplying = false;
            } catch (error) {
                console.error('Failed to apply filter:', error);
                this.state.isApplying = false;
                
                // Show notification
                this.notification.add('Error applying shop filter. Please try again.', {
                    type: 'danger'
                });
                
                // Fallback to URL method if action fails
                if (selectedShops && selectedShops.length > 0) {
                    window.location.href = this.buildFilterUrl(domain);
                }
            }
        }
        
        // Build URL with filter domain - improved implementation
        buildFilterUrl(domain) {
            // Get base URL without query parameters
            const baseUrl = window.location.href.split('?')[0];
            
            // Create a proper domain parameter that Odoo can understand
            // We need to escape it properly for URL use
            let domainStr = JSON.stringify(domain);
            domainStr = encodeURIComponent(domainStr);
            
            // Check if the page already has a question mark
            const separator = baseUrl.includes('?') ? '&' : '?';
            
            // Preserve view_type parameter if present
            const viewType = window.location.href.includes('view_type=list') ? 'list' : 'kanban';
            
            // Construct the final URL with domain filter
            return `${baseUrl}${separator}domain=${domainStr}&view_type=${viewType}`;
        }
    }

    // Register as a systray menu item
    registry.category('systray').add('inventory_button.shop_filter', {
        Component: ShopFilterMenu,
        sequence: 15
    });
});