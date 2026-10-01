/**
 * LOFT Design - Affiliate Dashboard Cart JS
 * Wizard navigation, commune cascade, qty controls, cart management
 * Note: Custom-select toggle behavior is handled by index.js (global).
 * This file only handles dynamic commune population + item binding.
 */

document.addEventListener("DOMContentLoaded", function () {
    var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (csrfToken) csrfToken = csrfToken.value;

    /* ── Commune cascade (wilaya → commune) ── */
    var communesDataEl = document.getElementById("dash-communes-data");
    if (communesDataEl) {
        var communesData = JSON.parse(communesDataEl.textContent);
        var wilayaWrapper = document.getElementById("dash-wilaya");
        var communeWrapper = document.getElementById("dash-commune");

        if (wilayaWrapper && communeWrapper) {
            var wilayaDisplay = wilayaWrapper.querySelector(".custom-select-display");
            var wilayaInput = wilayaWrapper.querySelector("input[type='hidden']");
            var communeList = communeWrapper.querySelector(".custom-select-list");
            var communeDisplay = communeWrapper.querySelector(".custom-select-display");
            var communeInput = communeWrapper.querySelector("input[type='hidden']");

            function populateCommunes(wilayaId) {
                communeList.innerHTML = "";
                communeDisplay.innerHTML = "Select commune <span class=\"arrow\"><i class=\"fas fa-caret-down\"></i></span>";
                communeInput.value = "";

                if (!wilayaId || !communesData[wilayaId]) return;

                communesData[wilayaId].forEach(function (opt) {
                    var item = document.createElement("li");
                    item.setAttribute("data-value", opt.value);
                    item.textContent = opt.label;
                    communeList.appendChild(item);
                });

                communeList.querySelectorAll("li").forEach(function (item) {
                    item.addEventListener("click", function (ce) {
                        ce.stopPropagation();
                        communeInput.value = item.getAttribute("data-value");
                        communeDisplay.innerHTML = item.textContent + ' <span class="arrow"><i class="fas fa-caret-down"></i></span>';
                        communeList.classList.remove("show");
                        communeWrapper.querySelector(".custom-select-display").classList.remove("active");
                        communeWrapper.classList.remove("active");
                    });
                });
            }

            // index.js changes display.innerHTML on selection → observe childList
            var observer = new MutationObserver(function () {
                var val = wilayaInput.value;
                if (val) populateCommunes(val);
            });
            observer.observe(wilayaDisplay, { childList: true, subtree: true });
        }
    }

    /* ── Wizard Step Navigation ── */
    var currentStep = 1;
    var totalSteps = 3;

    function goToStep(step) {
        if (step < 1 || step > totalSteps) return;
        currentStep = step;

        document.querySelectorAll(".wizard-panel").forEach(function (p) {
            p.classList.toggle("active", parseInt(p.dataset.panel) === step);
        });

        document.querySelectorAll(".wizard-step").forEach(function (s) {
            var sNum = parseInt(s.dataset.step);
            s.classList.remove("active", "completed");
            if (sNum === step) s.classList.add("active");
            else if (sNum < step) s.classList.add("completed");
        });

        document.querySelectorAll(".wizard-connector").forEach(function (c) {
            var cNum = parseInt(c.dataset.connector);
            c.classList.toggle("completed", cNum < step);
        });

        document.getElementById("wizardStepper").scrollIntoView({ behavior: "smooth", block: "center" });
    }

    document.querySelectorAll(".next-step").forEach(function (btn) {
        btn.addEventListener("click", function () {
            goToStep(parseInt(this.dataset.next));
        });
    });

    document.querySelectorAll(".prev-step").forEach(function (btn) {
        btn.addEventListener("click", function () {
            goToStep(parseInt(this.dataset.prev));
        });
    });

    /* ── Add to Cart ── */
    document.querySelectorAll(".add-to-cart-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var productPk = this.dataset.productPk;
            var qtyInput = this.closest(".add-row").querySelector(".cart-qty-input");
            var quantity = parseInt(qtyInput.value) || 1;

            fetch("/dashboard/orders/cart/" + productPk + "/add/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: new URLSearchParams({ quantity: quantity })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    window.location.reload();
                } else {
                    Swal.fire({
                        icon: "error",
                        title: data.message || gettext("Error"),
                        confirmButtonColor: "#b79454",
                        customClass: { popup: "rounded-4 border-0" }
                    });
                }
            })
            .catch(function () {
                Swal.fire({
                    icon: "error",
                    title: gettext("Something went wrong"),
                    confirmButtonColor: "#b79454",
                    customClass: { popup: "rounded-4 border-0" }
                });
            });
        });
    });

    /* ── Quantity Increment / Decrement ── */
    document.querySelectorAll(".qty-inc").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var productPk = this.dataset.productPk;
            var max = parseInt(this.dataset.max) || 999;
            var valueEl = this.parentElement.querySelector(".qty-value");
            var current = parseInt(valueEl.textContent) || 1;
            var newQty = current + 1;

            if (newQty > max) {
                Swal.fire({
                    icon: "warning",
                    title: interpolate(gettext("Only %s available"), [max]),
                    confirmButtonColor: "#b79454",
                    customClass: { popup: "rounded-4 border-0" }
                });
                return;
            }

            fetch("/dashboard/orders/cart/" + productPk + "/add/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: new URLSearchParams({ quantity: newQty })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    window.location.reload();
                }
            });
        });
    });

    document.querySelectorAll(".qty-dec").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var productPk = this.dataset.productPk;
            var valueEl = this.parentElement.querySelector(".qty-value");
            var current = parseInt(valueEl.textContent) || 1;
            var newQty = current - 1;

            if (newQty < 1) {
                Swal.fire({
                    title: this.dataset.swalTitle || gettext("Remove from cart?"),
                    text: (this.dataset.swalText || gettext("Remove")) + " \"" + this.dataset.title + "\"?",
                    icon: "question",
                    showCancelButton: true,
                    confirmButtonText: this.dataset.swalConfirm || gettext("Yes, remove"),
                    cancelButtonText: this.dataset.swalCancel || gettext("Cancel"),
                    confirmButtonColor: "#dc3545",
                    cancelButtonColor: "#6c757d",
                    customClass: {
                        popup: "rounded-4 border-0",
                        confirmButton: "rounded-pill px-4",
                        cancelButton: "rounded-pill px-4"
                    }
                }).then(function (result) {
                    if (!result.isConfirmed) return;

                    fetch("/dashboard/orders/cart/" + productPk + "/remove/", {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": csrfToken,
                            "X-Requested-With": "XMLHttpRequest"
                        }
                    })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data.success) window.location.reload();
                    });
                });
                return;
            }

            fetch("/dashboard/orders/cart/" + productPk + "/add/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: new URLSearchParams({ quantity: newQty })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    window.location.reload();
                }
            });
        });
    });

    /* ── Remove from Cart (cart review step) ── */
    document.querySelectorAll(".cart-review-item .remove-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var productPk = this.dataset.productPk;
            var title = this.dataset.title;

            Swal.fire({
                title: this.dataset.swalTitle || gettext("Remove from cart?"),
                text: (this.dataset.swalText || gettext("Remove")) + " \"" + title + "\"?",
                icon: "question",
                showCancelButton: true,
                confirmButtonText: this.dataset.swalConfirm || gettext("Yes, remove"),
                cancelButtonText: this.dataset.swalCancel || gettext("Cancel"),
                confirmButtonColor: "#dc3545",
                cancelButtonColor: "#6c757d",
                customClass: {
                    popup: "rounded-4 border-0",
                    confirmButton: "rounded-pill px-4",
                    cancelButton: "rounded-pill px-4"
                }
            }).then(function (result) {
                if (!result.isConfirmed) return;

                fetch("/dashboard/orders/cart/" + productPk + "/remove/", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest"
                    }
                })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) window.location.reload();
                });
            });
        });
    });

    /* ── Place Order ── */
    var orderForm = document.getElementById("dashOrderForm");
    if (orderForm) {
        orderForm.addEventListener("submit", function (e) {
            e.preventDefault();

            var name = this.querySelector("[name=name]").value.trim();
            var phone = this.querySelector("[name=phone]").value.trim();

            if (!name || !phone) {
                Swal.fire({
                    icon: "warning",
                    title: gettext("Missing fields"),
                    text: gettext("Name and phone are required."),
                    confirmButtonColor: "#b79454",
                    customClass: { popup: "rounded-4 border-0" }
                });
                return;
            }

            Swal.fire({
                title: orderForm.dataset.swalConfirmTitle || gettext("Confirm Order?"),
                html: (orderForm.dataset.swalConfirmHtml || gettext("Create order for")) + " <strong>" + name + "</strong>?",
                icon: "question",
                showCancelButton: true,
                confirmButtonText: orderForm.dataset.swalConfirmText || gettext("Yes, place order"),
                cancelButtonText: orderForm.dataset.swalCancelText || gettext("Cancel"),
                confirmButtonColor: "#198754",
                cancelButtonColor: "#6c757d",
                customClass: {
                    popup: "rounded-4 border-0",
                    confirmButton: "rounded-pill px-4",
                    cancelButton: "rounded-pill px-4"
                }
            }).then(function (result) {
                if (!result.isConfirmed) return;

                var formData = new FormData(orderForm);

                fetch("/dashboard/orders/cart/", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: new URLSearchParams(formData)
                })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) {
                        Swal.fire({
                            icon: "success",
                            title: data.message || gettext("Order Created!"),
                            confirmButtonColor: "#b79454",
                            customClass: { popup: "rounded-4 border-0" }
                        }).then(function () {
                            window.location.href = data.redirect_url;
                        });
                    } else {
                        Swal.fire({
                            icon: "error",
                            title: data.message || gettext("Error creating order"),
                            confirmButtonColor: "#b79454",
                            customClass: { popup: "rounded-4 border-0" }
                        });
                    }
                })
                .catch(function () {
                    Swal.fire({
                        icon: "error",
                        title: gettext("Something went wrong"),
                        confirmButtonColor: "#b79454",
                        customClass: { popup: "rounded-4 border-0" }
                    });
                });
            });
        });
    }
});
