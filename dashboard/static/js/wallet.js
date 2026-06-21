document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("withdrawForm");
    if (!form) return;

    var container = form.closest("[data-wallet-withdraw-url]");
    var withdrawUrl = container ? container.dataset.walletWithdrawUrl : "";
    var processingText = container ? container.dataset.processingText : "Processing...";
    var errorText = container ? container.dataset.errorText : "Error";
    var errorMsg = container ? container.dataset.errorMsg : "An error occurred.";
    var submitText = container ? container.dataset.submitText : "Submit Request";

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var btn = form.querySelector("button[type=submit]");
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>' + processingText;

        fetch(withdrawUrl, {
            method: "POST",
            body: new FormData(form),
            headers: {"X-Requested-With": "XMLHttpRequest"}
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                Swal.fire({
                    icon: "success",
                    text: data.message,
                    timer: 2000,
                    showConfirmButton: false
                }).then(function () { location.reload(); });
            } else {
                var errors = data.errors || {};
                var msgs = Object.values(errors).flat().join("\n");
                Swal.fire({icon: "error", text: msgs || data.message || errorText});
            }
        })
        .catch(function () {
            Swal.fire({icon: "error", text: errorMsg});
        })
        .finally(function () {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>' + submitText;
        });
    });
});
