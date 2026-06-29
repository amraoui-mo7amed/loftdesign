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
    const variantRows = document.querySelectorAll('#variantPicker .variant-row');
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

    // Modal elements
    const variantModal = document.getElementById('variantDetailModal');
    const modalThumb = variantModal && variantModal.querySelector('.modal-variant-thumb');
    const modalGalleryWrap = variantModal && variantModal.querySelector('.modal-variant-gallery-wrap');
    const modalName = document.getElementById('modalVariantName');
    const modalColorWrap = document.getElementById('modalVariantColor');
    const modalColorSwatch = modalColorWrap && modalColorWrap.querySelector('span:first-child');
    const modalColorText = modalColorWrap && modalColorWrap.querySelector('span:last-child');
    const modalDim = document.getElementById('modalVariantDim');
    const modalStock = document.getElementById('modalVariantStock');
    const modalStockBadge = modalStock && modalStock.querySelector('.badge');
    const modalSelectBtn = variantModal && variantModal.querySelector('.modal-select-variant');

    function selectVariant(row) {
        variantRows.forEach(function(r) { r.classList.remove('active'); });
        row.classList.add('active');

        var itemId = row.dataset.itemId;
        var itemName = row.dataset.itemName;
        var itemColor = row.dataset.itemColor;
        var itemDim = row.dataset.itemDimensions;
        var itemThumb = row.dataset.itemThumbnail;
        var itemGallery = row.dataset.itemGallery;
        var itemStock = parseInt(row.dataset.itemStock) || 0;
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
    }

    function openVariantModal(row) {
        if (!variantModal) return;

        var itemName = row.dataset.itemName;
        var itemColor = row.dataset.itemColor;
        var itemDim = row.dataset.itemDimensions;
        var itemThumb = row.dataset.itemThumbnail;
        var itemGallery = row.dataset.itemGallery;
        var itemStock = parseInt(row.dataset.itemStock) || 0;

        if (modalName) modalName.textContent = itemName;

        if (modalColorSwatch && modalColorText) {
            if (itemColor) {
                modalColorSwatch.style.background = itemColor.toLowerCase();
                modalColorText.textContent = itemColor;
                modalColorWrap.classList.remove('d-none');
            } else {
                modalColorWrap.classList.add('d-none');
            }
        }

        if (modalDim) {
            modalDim.textContent = itemDim || '';
            modalDim.classList.toggle('d-none', !itemDim);
        }

        if (modalThumb && itemThumb) {
            modalThumb.src = itemThumb;
            modalThumb.alt = itemName;
            modalThumb.style.display = '';
        } else if (modalThumb) {
            modalThumb.style.display = 'none';
        }

        if (modalStockBadge) {
            if (itemStock > 0) {
                modalStockBadge.textContent = itemStock + ' In Stock';
                modalStockBadge.className = 'badge bg-success fs-6 px-3 py-2';
            } else {
                modalStockBadge.textContent = 'Sold Out';
                modalStockBadge.className = 'badge bg-danger fs-6 px-3 py-2';
            }
        }

        if (modalGalleryWrap) {
            modalGalleryWrap.innerHTML = '';
            if (itemGallery) {
                var images = itemGallery.split(',');
                images.forEach(function(src) {
                    var img = document.createElement('img');
                    img.src = src;
                    img.alt = '';
                    img.className = 'rounded-2';
                    img.style.cssText = 'width: 60px; height: 60px; object-fit: cover; cursor: pointer; border: 2px solid transparent; transition: border-color 0.15s;';
                    img.addEventListener('click', function() {
                        if (modalThumb) modalThumb.src = src;
                        modalGalleryWrap.querySelectorAll('img').forEach(function(i) {
                            i.style.borderColor = 'transparent';
                        });
                        img.style.borderColor = '#000';
                    });
                    modalGalleryWrap.appendChild(img);
                });
                var firstGalleryImg = modalGalleryWrap.querySelector('img');
                if (firstGalleryImg) firstGalleryImg.style.borderColor = '#000';
            }
        }

        if (modalSelectBtn) {
            modalSelectBtn.dataset.targetItemId = row.dataset.itemId;
        }

        var bsModal = new bootstrap.Modal(variantModal);
        bsModal.show();
    }

    if (variantRows.length > 0) {
        variantRows.forEach(function(row) {
            row.addEventListener('click', function(e) {
                if (e.target.closest('.view-variant-btn')) return;
                selectVariant(this);
            });
        });

        var viewBtns = document.querySelectorAll('#variantPicker .view-variant-btn');
        viewBtns.forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                var row = this.closest('.variant-row');
                if (row) openVariantModal(row);
            });
        });

        if (modalSelectBtn) {
            modalSelectBtn.addEventListener('click', function() {
                var targetId = this.dataset.targetItemId;
                var targetRow = document.querySelector('#variantPicker .variant-row[data-item-id="' + targetId + '"]');
                if (targetRow) selectVariant(targetRow);
                var bsModal = bootstrap.Modal.getInstance(variantModal);
                if (bsModal) bsModal.hide();
            });
        }
    }
});
