odoo.define('inventory_button.ShopFilterMenu', function (require) {
    "use strict";

    const { Component, useState, onWillStart } = owl;
    const { Dropdown } = require('@web/core/dropdown/dropdown');
    const { DropdownItem } = require('@web/core/dropdown/dropdown_item');
    const { useService } = require('@web/core/utils/hooks');
    
    /**
     * Shop Filter Menu Component
     *
     * This component displays a dropdown menu with all available shops/stores
     * and allows filtering records by the selected shop.
     */
    class ShopFilterMenu extends Component {
        static template = 'inventory_button.ShopFilterMenu';
        static components = { Dropdown, DropdownItem };
        static props = {};
        
        setup() {
            this.rpc = useService('rpc');
            this.actionService = useService('action');
            
            this.state = useState({
                shops: [],
                selectedShops: [],
                searchValue: "",
                isLoaded: false
            });
            
            onWillStart(() => this.loadShops());
        }
        
        async loadShops() {
            try {
                const shops = await this.rpc('/web/dataset/call_kw', {
                    model: 'api.product',
                    method: 'get_all_shops',
                    args: [],
                    kwargs: {},
                });
                
                this.state.shops = shops.map(shop => ({
                    id: shop.store_id,
                    name: shop.store_name || `Store ${shop.store_id}`,
                    color: shop.store_color || '#CCCCCC',
                    selected: false
                }));
                
                this.state.isLoaded = true;
            } catch (error) {
                console.error('Failed to load shops:', error);
            }
        }
        
        get displayedShops() {
            if (!this.state.shops.length) {
                return [];
            }
            
            // Filter shops based on search value
            if (this.state.searchValue) {
                return this.state.shops.filter(shop => 
                    shop.name.toLowerCase().includes(this.state.searchValue.toLowerCase())
                );
            }
            return this.state.shops;
        }
        
        get hasSelectedShops() {
            return this.state.shops.some(shop => shop.selected);
        }
        
        get selectedCount() {
            return this.state.shops.filter(shop => shop.selected).length;
        }
        
        toggleShop(shopId) {
            const shopIndex = this.state.shops.findIndex(s => s.id === shopId);
            if (shopIndex >= 0) {
                this.state.shops[shopIndex].selected = !this.state.shops[shopIndex].selected;
                this.applyFilter();
            }
        }
        
        clearAll() {
            this.state.shops.forEach(shop => shop.selected = false);
            this.applyFilter();
        }
        
        selectAll() {
            this.state.shops.forEach(shop => shop.selected = true);
            this.applyFilter();
        }
        
        updateSearchValue(ev) {
            this.state.searchValue = ev.target.value || '';
        }
        
        applyFilter() {
            const selectedShops = this.state.shops.filter(shop => shop.selected);
            
            // Build domain filter
            let domain = [];
            
            if (selectedShops.length > 0) {
                const shopIds = selectedShops.map(shop => shop.id);
                domain = [['store_id', 'in', shopIds]];
            }
            
            // Apply the filter via action update
            this.actionService.doAction({
                type: 'ir.actions.act_window_update',
                target: 'current',
                domain: domain
            });
        }
    }

    return ShopFilterMenu;
});