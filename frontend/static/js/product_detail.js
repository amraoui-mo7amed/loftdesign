/**
 * LOFT Design - Product Detail Page
 * Handles custom searchable dropdowns for locations & variant selection
 */

document.addEventListener('DOMContentLoaded', () => {
    const communesDataEl = document.getElementById('communes-data');
    
    const formEl = document.getElementById('checkoutForm') || document.getElementById('orderForm');
    const l10n = formEl ? formEl.dataset : { 
        selectWilayaFirst: 'Please select a wilaya first', 
        selectCommune: 'Select Commune' 
    };

    if (communesDataEl) {
        const communesData = JSON.parse(communesDataEl.textContent);

        // Initialize Wilaya Select
        initSearchableSelect('wilaya-searchable', (value) => {
            updateCommunes(value);
        });

        // Initialize Commune Select (empty initially)
        initSearchableSelect('commune-searchable');

        function updateCommunes(wilayaId) {
            const list = document.querySelector('#commune-searchable .searchable-select-list');
            const display = document.querySelector('#commune-searchable .selected-text');
            const hiddenInput = document.querySelector('#commune-searchable input[type="hidden"]');
            
            list.innerHTML = '';
            display.textContent = l10n.selectCommune;
            hiddenInput.value = '';

            if (!wilayaId || !communesData[wilayaId]) return;

            const options = communesData[wilayaId];
            options.forEach(opt => {
                const li = document.createElement('li');
                li.setAttribute('data-value', opt.value);
                li.textContent = opt.label;
                list.appendChild(li);
            });

            bindListItems('commune-searchable');
        }
    }

    function initSearchableSelect(containerId, onChange) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const display = container.querySelector('.searchable-select-display');
        const dropdown = container.querySelector('.searchable-select-dropdown');
        const searchInput = container.querySelector('.search-input');
        
        display.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.searchable-select-dropdown.show').forEach(d => {
                if (d !== dropdown) d.classList.remove('show');
            });
            dropdown.classList.toggle('show');
            if (dropdown.classList.contains('show')) searchInput.focus();
        });

        searchInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            const items = container.querySelectorAll('.searchable-select-list li');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.classList.toggle('d-none', !text.includes(term));
            });
        });

        bindListItems(containerId, onChange);

        document.addEventListener('click', () => {
            dropdown.classList.remove('show');
        });
    }

    function bindListItems(containerId, onChange) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const display = container.querySelector('.selected-text');
        const hiddenInput = container.querySelector('input[type="hidden"]');
        const dropdown = container.querySelector('.searchable-select-dropdown');
        const items = container.querySelectorAll('.searchable-select-list li');

        items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const value = item.getAttribute('data-value');
                const text = item.textContent;

                items.forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                display.textContent = text;
                hiddenInput.value = value;
                dropdown.classList.remove('show');

                if (onChange) onChange(value);
            });
        });
    }

    // ── Variant Picker ──────────────────────────────────────────────
    const variantBtns = document.querySelectorAll('#variantPicker .variant-btn');
    const addToCartBtns = document.querySelectorAll('.btn-add-to-cart[data-product-id]');
    const orderItemIds = [
        document.getElementById('orderItemId'),
        document.getElementById('affOrderItemId'),
    ].filter(Boolean);
    const stockText = document.getElementById('stockText');
    const stockDot = document.getElementById('stockDot');
    const affStockText = document.getElementById('affStockText');
    const affStockDot = document.getElementById('affStockDot');
    const galleryMainImg = document.getElementById('galleryMainImg');
    const galleryThumbs = document.getElementById('galleryThumbs');
    const selectedVariantInfo = document.getElementById('selectedVariantInfo');
    const selectedVariantName = document.getElementById('selectedVariantName');
    const selectedVariantDim = document.getElementById('selectedVariantDim');

    if (variantBtns.length > 0) {
        variantBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                variantBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                var itemId = this.dataset.itemId;
                var itemName = this.dataset.itemName;
                var itemColor = this.dataset.itemColor;
                var itemDim = this.dataset.itemDimensions;
                var itemThumb = this.dataset.itemThumbnail;
                var itemGallery = this.dataset.itemGallery;
                var itemStock = parseInt(this.dataset.itemStock) || 0;
                var inStock = itemStock > 0;

                // Update Add to Cart buttons
                addToCartBtns.forEach(function(b) { b.dataset.itemId = itemId; });

                // Update order form hidden inputs
                orderItemIds.forEach(function(el) { el.value = itemId; });

                // Update stock displays
                if (stockText) stockText.textContent = inStock ? 'In Stock' : 'Out of Stock';
                if (affStockText) affStockText.textContent = inStock ? 'In Stock' : 'Out of Stock';

                // Update selected variant info
                if (selectedVariantInfo) {
                    var img = selectedVariantInfo.querySelector('img');
                    if (img && itemThumb) img.src = itemThumb;
                    if (selectedVariantName) selectedVariantName.textContent = itemName;
                    if (selectedVariantDim) {
                        selectedVariantDim.textContent = itemDim || '';
                        selectedVariantDim.classList.toggle('d-none', !itemDim);
                    }
                }

                // Swap gallery images if item has its own
                if (itemThumb && galleryMainImg) {
                    galleryMainImg.src = itemThumb;
                    if (galleryThumbs) {
                        var thumbs = galleryThumbs.querySelectorAll('.gallery-thumb');
                        if (itemGallery) {
                            var images = itemGallery.split(',');
                            thumbs.forEach(function(t, idx) {
                                if (idx === 0) {
                                    t.querySelector('img').src = itemThumb;
                                } else if (images[idx - 1]) {
                                    t.querySelector('img').src = images[idx - 1];
                                }
                            });
                        }
                        var first = galleryThumbs.querySelector('.gallery-thumb');
                        if (first) {
                            galleryThumbs.querySelectorAll('.gallery-thumb').forEach(function(t) {
                                t.classList.remove('active');
                            });
                            first.classList.add('active');
                        }
                    }
                }
            });
        });
    }
});
