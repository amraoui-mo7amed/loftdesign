document.addEventListener("DOMContentLoaded", function () {
    var csrfToken = getCSRFToken();

    // -------------------------------------------------------
    // Helper: Get CSRF
    // -------------------------------------------------------
    function getCSRFToken() {
        var meta = document.querySelector("[name=csrfmiddlewaretoken]");
        if (meta) return meta.value;
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.startsWith("csrftoken=")) return c.substring(10);
        }
        return "";
    }

    // -------------------------------------------------------
    // Event Delegation
    // -------------------------------------------------------
    document.addEventListener("click", function (e) {
        // Add to cart
        if (e.target.closest(".btn-add-to-cart")) {
            var btn = e.target.closest(".btn-add-to-cart");
            var productId = btn.dataset.productId;
            var itemId = btn.dataset.itemId;
            addToCart(productId, itemId, 1, btn);
        }
        // Cart drawer close/open
        if (e.target.closest("#cartIcon") || e.target.closest(".cart-trigger")) {
            e.preventDefault();
            openDrawer();
        }
        if (e.target.closest("#cartDrawerClose") || e.target.closest("#cartOverlay")) {
            closeDrawer();
        }
        // Quantity Plus/Minus
        if (e.target.closest(".cart-qty-plus")) {
            var btn = e.target.closest(".cart-qty-plus");
            var input = btn.parentElement.querySelector(".cart-qty-input");
            var val = parseInt(input.value) || 1;
            input.value = val + 1;
            updateCartItem(btn.dataset.itemId, val + 1);
        }
        if (e.target.closest(".cart-qty-minus")) {
            var btn = e.target.closest(".cart-qty-minus");
            var input = btn.parentElement.querySelector(".cart-qty-input");
            var val = parseInt(input.value) || 1;
            if (val > 1) {
                input.value = val - 1;
                updateCartItem(btn.dataset.itemId, val - 1);
            }
        }
        // Remove item
        if (e.target.closest(".cart-item-remove")) {
            var btn = e.target.closest(".cart-item-remove");
            removeCartItem(btn.dataset.itemId);
        }
        // Variant switch on cart page (list rows)
        if (e.target.closest(".variant-switch-row:not(.active):not(.out-of-stock)")) {
            var row = e.target.closest(".variant-switch-row:not(.active):not(.out-of-stock)");
            if (e.target.closest(".cart-view-variant-btn")) return;
            switchVariant(row.dataset.oldItemId, row.dataset.newItemId, row);
        }
        // View variant details from cart
        if (e.target.closest(".cart-view-variant-btn")) {
            var btn = e.target.closest(".cart-view-variant-btn");
            var row = btn.closest(".variant-switch-row");
            if (row) openCartVariantModal(row);
        }
        // Modal select variant button in cart
        if (e.target.closest(".modal-select-variant")) {
            var selectBtn = e.target.closest(".modal-select-variant");
            var oldId = selectBtn.dataset.oldItemId;
            var newId = selectBtn.dataset.newItemId;
            if (oldId && newId) {
                var targetRow = document.querySelector('.variant-switch-row[data-old-item-id="' + oldId + '"][data-new-item-id="' + newId + '"]');
                if (targetRow && !targetRow.classList.contains("active") && !targetRow.classList.contains("out-of-stock")) {
                    switchVariant(oldId, newId, targetRow);
                }
            }
            var modalEl = document.getElementById('variantDetailModal');
            var bsModal = bootstrap.Modal.getInstance(modalEl);
            if (bsModal) bsModal.hide();
        }
        // Legacy variant switch buttons (backward compat)
        if (e.target.closest(".variant-switch-btn:not([disabled])")) {
            var btn = e.target.closest(".variant-switch-btn:not([disabled])");
            switchVariant(btn.dataset.oldItemId, btn.dataset.newItemId, btn);
        }
    });

    // -------------------------------------------------------
    // Drawer functions
    // -------------------------------------------------------
    var cartDrawer = document.getElementById("cartDrawer");
    var cartOverlay = document.getElementById("cartOverlay");
    var cartItemsList = document.getElementById("cartItemsList");
    var cartEmpty = document.getElementById("cartEmpty");
    var cartFooter = document.getElementById("cartDrawerFooter");
    var drawerCount = document.getElementById("drawerCount");
    var drawerTotal = document.getElementById("drawerTotal");

    function openDrawer() {
        if (cartDrawer) cartDrawer.classList.add("open");
        if (cartOverlay) cartOverlay.classList.add("open");
        document.body.style.overflow = "hidden";
        loadCart();
    }

    function closeDrawer() {
        if (cartDrawer) cartDrawer.classList.remove("open");
        if (cartOverlay) cartOverlay.classList.remove("open");
        document.body.style.overflow = "";
    }

    function loadCart() {
        fetch("/cart/load/", {
            method: "GET",
            headers: { "X-Requested-With": "XMLHttpRequest" },
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    renderCart(data);
                }
            });
    }

    function renderCart(data) {
        if (!cartItemsList) return;

        cartItemsList.innerHTML = "";
        if (data.items.length === 0) {
            if (cartEmpty) cartEmpty.classList.remove("d-none");
            cartItemsList.classList.add("d-none");
            if (cartFooter) cartFooter.classList.add("d-none");
            if (drawerCount) drawerCount.textContent = "0";
            return;
        }

        if (cartEmpty) cartEmpty.classList.add("d-none");
        cartItemsList.classList.remove("d-none");
        if (cartFooter) cartFooter.classList.remove("d-none");
        if (drawerCount) drawerCount.textContent = data.total_items;
        if (drawerTotal) drawerTotal.textContent = data.total_display || (data.total_price + " DZD");

        data.items.forEach(function (item) {
            var itemDiv = document.createElement("div");
            itemDiv.className = "cart-item";
            itemDiv.dataset.itemId = item.id;
            itemDiv.innerHTML = `
                <div class="cart-item-img">
                    <img src="${item.thumbnail}" alt="${item.title}" onerror="this.style.display='none'">
                </div>
                <div class="cart-item-info">
                    <a href="${item.url}" class="cart-item-title">${item.title}</a>
                    <div class="cart-item-price">${item.price_display || (item.price + " DZD")}</div>
                    <div class="cart-item-controls">
                        <div class="cart-qty-selector">
                            <button type="button" class="cart-qty-minus" data-item-id="${item.id}">−</button>
                            <input type="number" class="cart-qty-input" value="${item.quantity}" min="1" data-item-id="${item.id}">
                            <button type="button" class="cart-qty-plus" data-item-id="${item.id}">+</button>
                        </div>
                        <button type="button" class="cart-item-remove" data-item-id="${item.id}" title="{% trans 'Remove' %}">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </div>
            `;
            cartItemsList.appendChild(itemDiv);
        });
    }

    function addToCart(productId, itemId, quantity, btn) {
        var formData = new FormData();
        formData.append("product_id", productId);
        formData.append("quantity", quantity);
        if (itemId) formData.append("item_id", itemId);

        var originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        fetch("/cart/add/", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrfToken,
            },
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    updateBadge(data.cart_total);
                    showMiniNotif(data.message);
                    openDrawer();
                } else {
                    showMiniNotif(data.message || gettext("Error"));
                }
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            })
            .catch(function () {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
                showMiniNotif("An error occurred.");
            });
    }

    function updateCartItem(itemId, quantity) {
        var formData = new FormData();
        formData.append("item_id", itemId);
        formData.append("quantity", quantity);

        fetch("/cart/update/", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrfToken,
            },
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    updateBadge(data.cart_total);
                    if (data.removed) {
                        var item = document.querySelector('.cart-item[data-item-id="' + itemId + '"]');
                        if (item) item.remove();
                        loadCart();
                    } else {
                        if (drawerTotal) drawerTotal.textContent = data.cart_total_display || (data.cart_total_price + " DZD");
                        var subEl = document.getElementById("subtotal-" + itemId);
                        if (subEl) subEl.textContent = data.item_subtotal_display || data.item_subtotal;
                    }
                    if (typeof reloadPageSummary === "function") reloadPageSummary(data.cart_total_display);
                }
            });
    }

    function removeCartItem(itemId) {
        var formData = new FormData();
        formData.append("item_id", itemId);

        fetch("/cart/remove/", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrfToken,
            },
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    updateBadge(data.cart_total);
                    loadCart();
                    var pageItem = document.querySelector('.cart-page-item[data-item-id="' + itemId + '"]');
                    if (pageItem) pageItem.remove();
                    if (typeof reloadPageSummary === "function") reloadPageSummary(data.cart_total_display);
                }
            });
    }

    function switchVariant(oldItemId, newItemId, element) {
        var formData = new FormData();
        formData.append("old_item_id", oldItemId);
        formData.append("new_item_id", newItemId);

        var isRow = element.classList.contains("variant-switch-row");
        var originalHtml, originalDisabled;
        if (!isRow) {
            originalHtml = element.innerHTML;
            originalDisabled = element.disabled;
            element.disabled = true;
            element.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        }

        fetch("/cart/switch-variant/", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrfToken,
            },
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    updateBadge(data.cart_total);
                    showMiniNotif(data.message);
                    if (data.item) {
                        var pageItem = document.querySelector('.cart-page-item[data-item-id="' + oldItemId + '"]');
                        if (pageItem) {
                            pageItem.dataset.itemId = newItemId;
                            var titleEl = pageItem.querySelector("h5");
                            if (titleEl) titleEl.textContent = data.item.title;
                            var thumbEl = pageItem.querySelector("img");
                            if (thumbEl) thumbEl.src = data.item.thumbnail;
                        }
                    }
                    // Update variant rows
                    var allRows = document.querySelectorAll('.variant-switch-row[data-old-item-id="' + oldItemId + '"]');
                    allRows.forEach(function (r) {
                        r.classList.remove("active");
                        var badge = r.querySelector(".badge.bg-dark.ms-1");
                        if (badge) badge.remove();
                        r.dataset.oldItemId = newItemId;
                    });
                    if (isRow) {
                        element.classList.add("active");
                        var nameEl = element.querySelector(".text-truncate");
                        if (nameEl) {
                            var badge = document.createElement("span");
                            badge.className = "badge bg-dark ms-1";
                            badge.style.cssText = "font-size:0.6rem;vertical-align:middle;";
                            badge.textContent = "Selected";
                            nameEl.appendChild(badge);
                        }
                    }
                    // Legacy buttons
                    var allBtns = document.querySelectorAll('.variant-switch-btn[data-old-item-id="' + oldItemId + '"]');
                    allBtns.forEach(function (b) {
                        b.disabled = false;
                        b.classList.remove("btn-dark");
                        b.classList.add("btn-outline-secondary");
                        if (b.dataset.originalHtml) b.innerHTML = b.dataset.originalHtml;
                    });
                    if (!isRow) {
                        element.classList.remove("btn-outline-secondary");
                        element.classList.add("btn-dark");
                        element.disabled = true;
                    }
                    if (typeof reloadPageSummary === "function") reloadPageSummary(data.cart_total_display);
                } else {
                    showMiniNotif(data.message || gettext("Error"));
                }
                if (!isRow) {
                    element.disabled = false;
                    element.innerHTML = originalHtml;
                }
            })
            .catch(function () {
                if (!isRow) {
                    element.disabled = false;
                    element.innerHTML = originalHtml;
                }
                showMiniNotif("An error occurred.");
            });
    }

    // ── Cart Variant Detail Modal ──────────────────────────────
    function openCartVariantModal(row) {
        var modal = document.getElementById('variantDetailModal');
        if (!modal) return;

        var itemName = row.dataset.itemName;
        var itemColor = row.dataset.itemColor;
        var itemDim = row.dataset.itemDimensions;
        var itemThumb = row.dataset.itemThumbnail;
        var itemGallery = row.dataset.itemGallery;
        var itemStock = parseInt(row.dataset.itemStock) || 0;

        var modalName = document.getElementById('modalVariantName');
        var modalColorWrap = document.getElementById('modalVariantColor');
        var modalColorSwatch = modalColorWrap && modalColorWrap.querySelector('span:first-child');
        var modalColorText = modalColorWrap && modalColorWrap.querySelector('span:last-child');
        var modalDim = document.getElementById('modalVariantDim');
        var modalThumb = modal.querySelector('.modal-variant-thumb');
        var modalGalleryWrap = modal.querySelector('.modal-variant-gallery-wrap');
        var modalStock = document.getElementById('modalVariantStock');
        var modalStockBadge = modalStock && modalStock.querySelector('.badge');
        var modalSelectBtn = modal.querySelector('.modal-select-variant');

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
            modalSelectBtn.dataset.oldItemId = row.dataset.oldItemId;
            modalSelectBtn.dataset.newItemId = row.dataset.newItemId;
        }

        var bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    function reloadPageSummary(display) {
        var totalEl = document.getElementById("orderTotal");
        var cartTotalEl = document.getElementById("summaryTotal");
        if (display) {
            if (totalEl) totalEl.textContent = display;
            if (cartTotalEl) cartTotalEl.textContent = display;
            return;
        }
        var subtotals = document.querySelectorAll(".cart-page-item-subtotal");
        var sum = 0;
        subtotals.forEach(function (el) {
            var val = parseFloat(el.textContent.replace(/[^0-9.]/g, ""));
            if (!isNaN(val)) sum += val;
        });
        if (totalEl) totalEl.textContent = sum.toLocaleString() + " DZD";
        if (cartTotalEl) cartTotalEl.textContent = sum.toLocaleString() + " DZD";
    }

    function updateBadge(count) {
        var badges = document.querySelectorAll(".cart-icon-badge, .cart-fab-badge");
        badges.forEach(function (badge) {
            badge.textContent = count;
            if (count === "0" || count === 0) {
                badge.classList.add("d-none");
            } else {
                badge.classList.remove("d-none");
            }
        });
    }

    function showMiniNotif(msg) {
        var div = document.createElement("div");
        div.className = "cart-mini-notif";
        div.textContent = msg;
        Object.assign(div.style, {
            position: "fixed", bottom: "24px", left: "50%", transform: "translateX(-50%)",
            background: "#212529", color: "#fff", padding: "12px 24px", borderRadius: "12px",
            fontWeight: "700", fontSize: "0.9rem", zIndex: "9999", boxShadow: "0 8px 30px rgba(0,0,0,0.15)",
            maxWidth: "90vw", textAlign: "center"
        });
        document.body.appendChild(div);
        setTimeout(function () { div.remove(); }, 2500);
    }
});
