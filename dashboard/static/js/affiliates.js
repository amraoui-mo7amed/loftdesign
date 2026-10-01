document.addEventListener("DOMContentLoaded", function () {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;

    const handleAffiliateAction = function (btn) {
        btn.addEventListener("click", function () {
            const config = {
                title: this.dataset.swalTitle,
                text: this.dataset.swalText,
                icon: this.dataset.swalIcon || "question",
                showCancelButton: true,
                confirmButtonText: this.dataset.swalConfirm,
                cancelButtonText: this.dataset.swalCancel,
                confirmButtonColor: this.dataset.swalConfirmColor || "#212529",
                customClass: {
                    popup: "rounded-5 border-0",
                    confirmButton: "rounded-pill px-4 py-2 fw-bold",
                    cancelButton: "rounded-pill px-4 py-2 fw-bold"
                }
            };

            Swal.fire(config).then(function (result) {
                if (!result.isConfirmed) return;

                const fetchOptions = {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest"
                    }
                };

                if (btn.dataset.formData) {
                    const formData = new FormData();
                    JSON.parse(btn.dataset.formData).forEach(function (pair) {
                        formData.append(pair[0], pair[1]);
                    });
                    fetchOptions.body = formData;
                }

                fetch(btn.dataset.url, fetchOptions)
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data.success) {
                            Swal.fire({
                                icon: "success",
                                title: data.message,
                                timer: 2000,
                                showConfirmButton: false,
                                customClass: { popup: "rounded-5" }
                            }).then(function () {
                                window.location.reload();
                            });
                        } else {
                            Swal.fire({
                                icon: "error",
                                title: data.message,
                                customClass: { popup: "rounded-5" }
                            });
                        }
                    })
                    .catch(function () {
                        Swal.fire({
                            icon: "error",
                            title: btn.dataset.swalError || gettext("An error occurred."),
                            customClass: { popup: "rounded-5" }
                        });
                    });
            });
        });
    };

    document.querySelectorAll(".approve-btn, .toggle-block-btn, .delete-btn, .affiliate-approve-btn, .commission-toggle-btn")
        .forEach(handleAffiliateAction);
});
