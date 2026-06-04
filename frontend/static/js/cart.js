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
            addToCart(productId, 1, btn);
        }
        // Cart drawer close/open
        if (e.target.closest("#cartIcon")) {
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
        if (drawerTotal) drawerTotal.textContent = data.total_price + " DZD";

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
                    <div class="cart-item-price">${item.price} DZD</div>
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

    function addToCart(productId, quantity, btn) {
        var formData = new FormData();
        formData.append("product_id", productId);
        formData.append("quantity", quantity);

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
                    showMiniNotif(data.message || "Error");
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
                        if (drawerTotal) drawerTotal.textContent = data.cart_total_price + " DZD";
                        var subEl = document.getElementById("subtotal-" + itemId);
                        if (subEl) subEl.textContent = data.item_subtotal;
                    }
                    if (typeof reloadPageSummary === "function") reloadPageSummary();
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
                    if (typeof reloadPageSummary === "function") reloadPageSummary();
                }
            });
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
