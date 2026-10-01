document.addEventListener("DOMContentLoaded", function () {
    // ── Partner Price Form ─────────────────────────────────────────
    var form = document.getElementById("partnerPriceForm");
    if (form) {
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

    // ── Delete Price (uses SweetAlert for confirmation) ────────────
    var deleteBtns = document.querySelectorAll(".delete-price");
    deleteBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            var url = this.dataset.url;
            var name = this.dataset.name;
            var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

            Swal.fire({
                title: this.dataset.swalTitle || gettext("Remove Price?"),
                text: (this.dataset.swalText || gettext("Remove custom price for")) + " " + name + "?",
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: this.dataset.swalConfirm || gettext("Yes, remove"),
                cancelButtonText: this.dataset.swalCancel || gettext("Cancel"),
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
                            window.location.href = data.redirect_url;
                        }
                    });
                }
            });
        });
    });
});
