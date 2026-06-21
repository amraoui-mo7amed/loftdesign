document.addEventListener("DOMContentLoaded", function () {
    var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;

    document.querySelectorAll(".clear-wallet-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            Swal.fire({
                title: this.dataset.swalTitle || "Clear Wallet?",
                text: this.dataset.swalText || "This will delete all transactions and reset balance to 0.",
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: this.dataset.swalConfirm || "Yes, clear it",
                cancelButtonText: this.dataset.swalCancel || "Cancel",
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
                        Swal.fire({ icon: "error", text: data.message || "Error", customClass: { popup: "rounded-5" } });
                    }
                })
                .catch(function () {
                    Swal.fire({ icon: "error", text: "An error occurred.", customClass: { popup: "rounded-5" } });
                });
            });
        });
    });
});
