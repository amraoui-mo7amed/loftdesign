document.addEventListener("DOMContentLoaded", function () {
    var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (csrfToken) {
        csrfToken = csrfToken.value;
    }

    // ── Create Affiliate Form ────────────────────────────────
    var form = document.getElementById("affiliateCreateForm");
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
                    var msgEl = document.getElementById("affiliateCreateSuccess");
                    if (msgEl) {
                        msgEl.textContent = data.message;
                        msgEl.classList.remove("d-none");
                    }
                    setTimeout(function () { location.reload(); }, 1500);
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

    // ── Delete Affiliate (SweetAlert confirmation) ──────────
    document.querySelectorAll(".affiliate-delete-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var url = this.dataset.url;
            var name = this.dataset.name;

            Swal.fire({
                title: this.dataset.swalTitle || gettext("Delete?"),
                text: (this.dataset.swalText || gettext("Delete")) + " " + name + "?",
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: this.dataset.swalConfirm || gettext("Yes, delete"),
                cancelButtonText: this.dataset.swalCancel || gettext("Cancel"),
                reverseButtons: true,
                customClass: {
                    popup: "rounded-4 border-0",
                    confirmButton: "rounded-pill px-4",
                    cancelButton: "rounded-pill px-4"
                }
            }).then(function (result) {
                if (!result.isConfirmed) return;
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
                            title: data.message || gettext("Deleted!"),
                            timer: 1500,
                            showConfirmButton: false,
                            customClass: { popup: "rounded-4 border-0" }
                        }).then(function () {
                            location.reload();
                        });
                    } else {
                        Swal.fire({
                            icon: "error",
                            title: data.message || gettext("An error occurred."),
                            customClass: { popup: "rounded-4 border-0" }
                        });
                    }
                });
            });
        });
    });
});