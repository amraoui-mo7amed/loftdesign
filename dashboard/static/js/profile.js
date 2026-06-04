document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("profileForm");
    if (!form) return;

    var errorContainer = document.getElementById("profileForm-errors");
    var l10n = form.dataset; // SuccessTitle, ErrorTitle, ErrorText

    var avatarRing = document.getElementById("avatarWrapper");
    var avatarPreview = document.getElementById("avatarPreview");
    var fileInput = document.getElementById("profilePictureInput");

    // -------------------------------------------------------
    // Avatar ring / camera button click -> open file picker
    // -------------------------------------------------------
    if (avatarRing) {
        avatarRing.addEventListener("click", function () {
            fileInput.click();
        });
    }

    // -------------------------------------------------------
    // File selected -> update avatar preview instantly
    // -------------------------------------------------------
    fileInput.addEventListener("change", function () {
        var file = this.files[0];
        if (file) {
            var reader = new FileReader();
            reader.onload = function (e) {
                var dataUrl = e.target.result;
                if (avatarPreview) {
                    if (avatarPreview.tagName === "IMG") {
                        avatarPreview.src = dataUrl;
                    } else {
                        var img = document.createElement("img");
                        img.src = dataUrl;
                        img.alt = "Profile";
                        img.className = "profile-avatar-img";
                        img.id = "avatarPreview";
                        avatarPreview.parentNode.replaceChild(img, avatarPreview);
                        avatarPreview = img;
                    }
                }
            };
            reader.readAsDataURL(file);
        }
    });

    // -------------------------------------------------------
    // Form submission via AJAX
    // -------------------------------------------------------
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        var formData = new FormData(form);
        var submitBtn = document.getElementById("saveProfileBtn");
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Saving...';
        }

        fetch(form.action, {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then(function (res) {
                return res.json();
            })
            .then(function (data) {
                if (data.success) {
                    Swal.fire({
                        icon: "success",
                        title: l10n.successTitle || "Success",
                        text: data.message,
                        timer: 2000,
                        showConfirmButton: false,
                    }).then(function () {
                        location.reload();
                    });
                } else {
                    if (errorContainer) {
                        var list = errorContainer.querySelector(".error-list");
                        if (list) list.innerHTML = "";
                        if (data.errors) {
                            Object.values(data.errors).forEach(function (errs) {
                                errs.forEach(function (msg) {
                                    var li = document.createElement("li");
                                    li.textContent = msg;
                                    if (list) list.appendChild(li);
                                });
                            });
                            errorContainer.classList.remove("d-none");
                        }
                    }
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<i class="fas fa-check me-2"></i> Save Changes';
                    }
                }
            })
            .catch(function () {
                Swal.fire({
                    icon: "error",
                    title: l10n.errorTitle || "Error",
                    text: l10n.errorText || "An unexpected error occurred.",
                });
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-check me-2"></i> Save Changes';
                }
            });
    });
});
