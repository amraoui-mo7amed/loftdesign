document.addEventListener("DOMContentLoaded", function () {
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
    // Form submission via AJAX — SweetAlert notifications
    // -------------------------------------------------------
    const form = document.getElementById("profileForm");
    if (!form) return;

    form.addEventListener("submit", function (e) {
        e.preventDefault();

        const formData = new FormData(form);

        // Manually append the file from the external file input
        var fileInput = document.getElementById("profilePictureInput");
        if (fileInput && fileInput.files.length) {
            formData.append("profile_picture", fileInput.files[0]);
        }

        const submitBtn = document.getElementById("saveProfileBtn");
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Saving...';
        }

        fetch(form.action, {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-check me-2"></i> Save Changes';
            }
            if (data.success) {
                Swal.fire({
                    icon: "success",
                    title: data.message || "Profile updated successfully.",
                    timer: 1500,
                    showConfirmButton: false,
                }).then(function () {
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    }
                });
                return;
            }
            if (data.errors) {
                var errorHtml = "";
                Object.values(data.errors).forEach(function (errs) {
                    errs.forEach(function (msg) {
                        errorHtml += "<li>" + msg + "</li>";
                    });
                });
                Swal.fire({
                    icon: "error",
                    title: "Validation Error",
                    html: "<ul class='mb-0 text-start'>" + errorHtml + "</ul>",
                });
            }
        })
        .catch(function () {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-check me-2"></i> Save Changes';
            }
            Swal.fire({
                icon: "error",
                title: "Error",
                text: "An unexpected error occurred.",
            });
        });
    });

});
