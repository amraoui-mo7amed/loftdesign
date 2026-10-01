document.addEventListener("DOMContentLoaded", function () {
    // ── Approve Modal ──────────────────────────────────────────────
    var approveBtns = document.querySelectorAll(".approve-btn");
    approveBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            var nameEl = document.getElementById("approveProductName");
            if (nameEl) {
                nameEl.innerHTML =
                    "<strong>" + this.dataset.product + "</strong>" +
                    '<br><span class="text-muted small">' +
                    (this.dataset.approveLabel || gettext("Set the pricing for this product")) +
                    "</span>";
            }
            var providerInfo = document.getElementById("approveProviderInfo");
            var providerName = document.getElementById("approveProviderName");
            var providerPriceWrap = document.getElementById("approveProviderPurchaseWrap");
            var providerPrice = document.getElementById("approveProviderPrice");
            var providerWholesale = document.getElementById("approveProviderWholesale");
            var providerRetail = document.getElementById("approveProviderRetail");
            if (providerInfo && providerName && providerPrice) {
                var pp = this.dataset.purchasePrice;
                var pn = this.dataset.providerName;
                var pw = this.dataset.providerWholesale;
                var pr = this.dataset.providerRetail;
                if (pn) {
                    providerName.textContent = pn;
                    if (pp) {
                        providerPrice.textContent = pp + " DZD";
                        if (providerPriceWrap) providerPriceWrap.classList.remove("d-none");
                    } else {
                        providerPrice.textContent = "";
                        if (providerPriceWrap) providerPriceWrap.classList.add("d-none");
                    }
                    providerWholesale.textContent = (pw ? pw + " DZD" : "—");
                    providerRetail.textContent = (pr ? pr + " DZD" : "—");
                    providerInfo.classList.remove("d-none");
                    // Pre-fill admin inputs with provider's suggestions
                    var wsInput = document.querySelector("#approveForm input[name='loft_wholesale_price']");
                    var rtInput = document.querySelector("#approveForm input[name='loft_retail_price']");
                    if (wsInput && pw) wsInput.value = pw;
                    if (rtInput && pr) rtInput.value = pr;
                } else {
                    providerInfo.classList.add("d-none");
                }
            }
            var form = document.getElementById("approveForm");
            if (form) form.action = this.dataset.url;
            var modal = new bootstrap.Modal(document.getElementById("approveModal"));
            modal.show();
        });
    });

    // ── Reject Modal ───────────────────────────────────────────────
    var rejectBtns = document.querySelectorAll(".reject-btn");
    rejectBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            var nameEl = document.getElementById("rejectProductName");
            if (nameEl) {
                nameEl.innerHTML = "<strong>" + this.dataset.product + "</strong>";
            }
            var form = document.getElementById("rejectForm");
            if (form) form.action = this.dataset.url;
            var modal = new bootstrap.Modal(document.getElementById("rejectModal"));
            modal.show();
        });
    });

    // ── Form AJAX Submission ──────────────────────────────────────
    function handleFormSubmit(formId) {
        var form = document.getElementById(formId);
        if (!form) return;

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            var formData = new FormData(this);
            var errorContainer = this.querySelector("#errorContainer");

            fetch(this.action, {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    window.location.href = data.redirect_url;
                } else {
                    var list = errorContainer ? errorContainer.querySelector("ul") : null;
                    if (list) {
                        list.innerHTML = "";
                        var errors = data.errors || {};
                        for (var key in errors) {
                            var msgs = errors[key];
                            if (Array.isArray(msgs)) {
                                msgs.forEach(function (m) {
                                    var li = document.createElement("li");
                                    li.textContent = m;
                                    list.appendChild(li);
                                });
                            }
                        }
                        errorContainer.classList.remove("d-none");
                    }
                }
            });
        });
    }

    handleFormSubmit("approveForm");
    handleFormSubmit("rejectForm");
});
