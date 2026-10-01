document.addEventListener("DOMContentLoaded", function () {
    var container = document.getElementById("withdrawalContainer");
    if (!container) return;

    var csrfToken = container.dataset.csrf;
    var handleUrl = container.dataset.handleUrl;

    var transApprove = container.dataset.transApprove || "approve";
    var transReject = container.dataset.transReject || "reject";
    var transConfirm = container.dataset.transConfirm || gettext("Confirm");
    var transConfirmText = container.dataset.transConfirmText || gettext("Are you sure you want to");
    var transThisWithdrawal = container.dataset.transThisWithdrawal || "this withdrawal?";
    var transYes = container.dataset.transYes || gettext("Yes");
    var transCancel = container.dataset.transCancel || gettext("Cancel");
    var transError = container.dataset.transError || gettext("Error");

    document.querySelectorAll(".approve-btn, .reject-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var id = this.dataset.id;
            var action = this.classList.contains("approve-btn") ? "approve" : "reject";
            var verb = action === "approve" ? transApprove : transReject;

            Swal.fire({
                title: transConfirm,
                text: transConfirmText + " " + verb + " " + transThisWithdrawal,
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: transYes,
                cancelButtonText: transCancel
            }).then(function (result) {
                if (!result.isConfirmed) return;

                fetch(handleUrl.replace("0", id), {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: new URLSearchParams({action: action})
                })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) {
                        Swal.fire({icon: "success", text: data.message, timer: 1500, showConfirmButton: false})
                            .then(function () { location.reload(); });
                    } else {
                        Swal.fire({icon: "error", text: data.message || transError});
                    }
                });
            });
        });
    });
});
