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
                    (this.dataset.approveLabel || "Set the pricing for this product") +
                    "</span>";
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
