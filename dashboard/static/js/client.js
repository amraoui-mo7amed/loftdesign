document.addEventListener("DOMContentLoaded", function () {

    /* ── Catalog: Buy Now modal ── */
    var buyModalEl = document.getElementById("buyModal");
    if (buyModalEl) {
        var modal = new bootstrap.Modal(buyModalEl);
        var qtyDisplay = document.getElementById("modalQtyDisplay");
        var qtyInput = document.getElementById("modalQty");
        var minusBtn = document.getElementById("qtyMinus");
        var plusBtn = document.getElementById("qtyPlus");
        var productIdInput = document.getElementById("modalProductId");
        var modalTitle = document.getElementById("buyModalLabel");
        var modalPrice = document.getElementById("modalPrice");
        var availableSpan = document.getElementById("modalAvailable");
        var buySubmit = document.getElementById("buySubmit");
        var errorContainer = document.getElementById("buyErrors");
        var maxQty = 1;

        function updateQty() {
            var val = parseInt(qtyInput.value, 10) || 1;
            if (val < 1) { val = 1; }
            if (val > maxQty) { val = maxQty; }
            qtyInput.value = val;
            if (qtyDisplay) { qtyDisplay.textContent = val; }
        }

        if (minusBtn) { minusBtn.addEventListener("click", function () {
            qtyInput.value = (parseInt(qtyInput.value, 10) || 1) - 1;
            updateQty();
        }); }

        if (plusBtn) { plusBtn.addEventListener("click", function () {
            qtyInput.value = (parseInt(qtyInput.value, 10) || 1) + 1;
            updateQty();
        }); }

        if (qtyInput) { qtyInput.addEventListener("input", updateQty); }

        // Open modal and populate from data attributes
        document.querySelectorAll(".open-buy-modal").forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                var card = this.closest("[data-product-id]");
                if (!card) return;
                productIdInput.value = card.dataset.productId;
                modalTitle.textContent = card.dataset.productTitle;
                modalPrice.textContent = card.dataset.productPrice + " DZD";
                maxQty = parseInt(card.dataset.availableQty, 10) || 1;
                availableSpan.textContent = maxQty;
                qtyInput.value = 1;
                updateQty();
                if (errorContainer) { errorContainer.classList.add("d-none"); }
                modal.show();
            });
        });

        // Submit buy order via AJAX
        if (buySubmit) {
            buySubmit.addEventListener("click", function () {
                var submitBtn = this;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> ' + submitBtn.dataset.loading || "Placing...";

                if (errorContainer) { errorContainer.classList.add("d-none"); }

                var formData = new FormData();
                formData.append("product_id", productIdInput.value);
                formData.append("quantity", qtyInput.value);
                formData.append("csrfmiddlewaretoken", document.querySelector("[name=csrfmiddlewaretoken]").value);

                fetch(submitBtn.dataset.url, {
                    method: "POST",
                    body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) {
                        modal.hide();
                        Swal.fire({
                            icon: "success",
                            title: data.message,
                            showConfirmButton: true,
                        }).then(function () {
                            if (data.redirect_url) { window.location.href = data.redirect_url; }
                        });
                    } else {
                        if (errorContainer) {
                            var list = errorContainer.querySelector("ul");
                            if (list) {
                                list.innerHTML = "";
                                for (var field in data.errors) {
                                    if (data.errors.hasOwnProperty(field)) {
                                        data.errors[field].forEach(function (msg) {
                                            var li = document.createElement("li");
                                            li.textContent = msg;
                                            list.appendChild(li);
                                        });
                                    }
                                }
                                errorContainer.classList.remove("d-none");
                            }
                        }
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<i class="fas fa-check me-2"></i> ' + submitBtn.dataset.label || "Place Order";
                    }
                })
                .catch(function () {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-check me-2"></i> ' + submitBtn.dataset.label || "Place Order";
                });
            });
        }
    }

    /* ── End Client List: delete with SweetAlert ── */
    document.querySelectorAll("[data-delete-url]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var url = this.dataset.deleteUrl;
            var name = this.dataset.deleteName;
            var csrf = document.querySelector("[name=csrfmiddlewaretoken]");
            Swal.fire({
                title: btn.dataset.swalTitle || "Delete?",
                text: btn.dataset.swalText || ('Permanently delete "' + name + '"? This cannot be undone.'),
                icon: "warning",
                showCancelButton: true,
                confirmButtonColor: "#d33",
                cancelButtonColor: "#6c757d",
                confirmButtonText: btn.dataset.swalConfirm || "Yes, delete",
                cancelButtonText: btn.dataset.swalCancel || "Cancel",
            }).then(function (result) {
                if (result.isConfirmed) {
                    fetch(url, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": csrf ? csrf.value : "",
                            "X-Requested-With": "XMLHttpRequest",
                        },
                    })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data.success) {
                            Swal.fire({
                                icon: "success",
                                title: btn.dataset.swalDeletedTitle || "Deleted!",
                                text: data.message,
                            });
                            setTimeout(function () { location.reload(); }, 1000);
                        } else {
                            Swal.fire({
                                icon: "error",
                                title: btn.dataset.swalErrorTitle || "Error",
                                text: data.message,
                            });
                        }
                    });
                }
            });
        });
    });
});
