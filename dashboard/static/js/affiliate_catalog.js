document.addEventListener("DOMContentLoaded", function () {
    var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (csrfToken) {
        csrfToken = csrfToken.value;
    }

    // ── Update Pricing Form ─────────────────────────────────────────
    var pricingForm = document.getElementById("updatePricingForm");
    if (pricingForm) {
        pricingForm.addEventListener("submit", function (e) {
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
                    Swal.fire({
                        icon: "success",
                        title: data.message || "Saved!",
                        timer: 1500,
                        showConfirmButton: false,
                        customClass: { popup: "rounded-4 border-0" }
                    }).then(function () {
                        location.reload();
                    });
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
                        if (list.children.length) errorContainer.classList.remove("d-none");
                    }
                }
            });
        });
    }

    // ── Add to Catalog ──────────────────────────────────────────────
    var addBtns = document.querySelectorAll(".add-catalog");
    addBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            var url = this.dataset.url;
            var name = this.dataset.name;

            fetch(url, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": csrfToken
                }
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    Swal.fire({
                        icon: "success",
                        title: data.message || "Added!",
                        timer: 1500,
                        showConfirmButton: false,
                        customClass: { popup: "rounded-4 border-0" }
                    }).then(function () {
                        location.reload();
                    });
                } else {
                    var msg = "Error";
                    if (data.errors) {
                        var all = [];
                        for (var k in data.errors) {
                            if (Array.isArray(data.errors[k])) {
                                all = all.concat(data.errors[k]);
                            }
                        }
                        if (all.length) msg = all.join(", ");
                    }
                    Swal.fire({
                        icon: "error",
                        title: msg,
                        customClass: {
                            popup: "rounded-4 border-0",
                            confirmButton: "rounded-pill px-4"
                        }
                    });
                }
            })
            .catch(function () {
                Swal.fire({
                    icon: "error",
                    title: "Network error",
                    customClass: {
                        popup: "rounded-4 border-0",
                        confirmButton: "rounded-pill px-4"
                    }
                });
            });
        });
    });

    // ── Remove from Catalog (SweetAlert confirmation) ──────────────
    var removeBtns = document.querySelectorAll(".remove-catalog");
    removeBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            var url = this.dataset.url;
            var name = this.dataset.name;

            Swal.fire({
                title: this.dataset.swalTitle || "Remove from Catalog?",
                text: (this.dataset.swalText || "Remove") + " " + name + "?",
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: this.dataset.swalConfirm || "Yes, remove",
                cancelButtonText: this.dataset.swalCancel || "Cancel",
                reverseButtons: true,
                customClass: {
                    popup: "rounded-4 border-0",
                    confirmButton: "rounded-pill px-4",
                    cancelButton: "rounded-pill px-4"
                }
            }).then(function (result) {
                if (result.isConfirmed) {
                    fetch(url, {
                        method: "POST",
                        headers: {
                            "X-Requested-With": "XMLHttpRequest",
                            "X-CSRFToken": csrfToken
                        }
                    })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data.success) {
                            location.reload();
                        }
                    });
                }
            });
        });
    });
});
