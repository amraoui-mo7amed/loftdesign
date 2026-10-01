document.addEventListener("DOMContentLoaded", function () {
    var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;

    document.querySelectorAll(".clear-wallet-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            Swal.fire({
                title: this.dataset.swalTitle || gettext("Clear Wallet?"),
                text: this.dataset.swalText || gettext("This will reset the balance to 0. The history is kept."),
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: this.dataset.swalConfirm || gettext("Yes, clear it"),
                cancelButtonText: this.dataset.swalCancel || gettext("Cancel"),
                confirmButtonColor: "#dc3545",
                customClass: { popup: "rounded-5 border-0", confirmButton: "rounded-pill px-4 py-2 fw-bold", cancelButton: "rounded-pill px-4 py-2 fw-bold" }
            }).then(function (result) {
                if (!result.isConfirmed) return;

                fetch(btn.dataset.url, {
                    method: "POST",
                    headers: { "X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest" }
                })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) {
                        Swal.fire({ icon: "success", text: data.message, timer: 1500, showConfirmButton: false, customClass: { popup: "rounded-5" } })
                            .then(function () { location.reload(); });
                    } else {
                        Swal.fire({ icon: "error", text: data.message || gettext("Error"), customClass: { popup: "rounded-5" } });
                    }
                })
                .catch(function () {
                    Swal.fire({ icon: "error", text: gettext("An error occurred."), customClass: { popup: "rounded-5" } });
                });
            });
        });
    });

    // Admin withdraw from user
    var adminForm = document.getElementById("adminWithdrawForm");
    if (adminForm) {
        var processingText = adminForm.closest("[data-processing-text]")
            ? adminForm.closest("[data-processing-text]").dataset.processingText
            : "Processing...";
        var withdrawUrl = adminForm.dataset.url;

        adminForm.addEventListener("submit", function (e) {
            e.preventDefault();
            var btn = adminForm.querySelector("button[type=submit]");
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>' + processingText;

            fetch(withdrawUrl, {
                method: "POST",
                body: new FormData(adminForm),
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    var modalEl = document.getElementById("adminWithdrawModal");
                    var modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                    Swal.fire({
                        icon: "success",
                        text: data.message,
                        timer: 2000,
                        showConfirmButton: false,
                        customClass: { popup: "rounded-5" }
                    }).then(function () { location.reload(); });
                } else {
                    var errors = data.errors || {};
                    var msgs = Object.values(errors).flat().join("\\n");
                    Swal.fire({ icon: "error", text: msgs || data.message || gettext("Error"), customClass: { popup: "rounded-5" } });
                }
            })
            .catch(function () {
                Swal.fire({ icon: "error", text: gettext("An error occurred."), customClass: { popup: "rounded-5" } });
            })
            .finally(function () {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-paper-plane me-2"></i> Confirm Withdrawal';
            });
        });
    }
});
