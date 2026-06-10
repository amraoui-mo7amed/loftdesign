document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("storeSettingsForm");
  if (!form) return;

  var colorPicker = form.querySelector("input[name='header_bg_color']");
  var colorText = form.querySelector("input[name='header_bg_color_text']");

  if (colorPicker && colorText) {
    colorPicker.addEventListener("input", function () {
      colorText.value = this.value;
    });
    colorText.addEventListener("input", function () {
      if (/^#[0-9a-f]{6}$/i.test(this.value)) {
        colorPicker.value = this.value;
      }
    });
  }

  var modalEl = document.getElementById("storeSettingsModal");
  if (modalEl) {
    modalEl.addEventListener("hidden.bs.modal", function () {
      var backdrop = document.querySelector(".modal-backdrop");
      if (backdrop) backdrop.remove();
      document.body.classList.remove("modal-open");
      document.body.style.overflow = "";
      document.body.style.paddingRight = "";
    });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var submitBtn = form.querySelector("button[type='submit']");
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Saving...';

    var formData = new FormData(form);

    fetch(form.action, {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.success) {
          var modal = bootstrap.Modal.getInstance(modalEl);
          if (modal) modal.hide();
          Swal.fire({
            icon: "success",
            title: "Saved",
            text: data.message,
            timer: 2000,
            showConfirmButton: false,
          }).then(function () {
            location.reload();
          });
        } else {
          Swal.fire({ icon: "error", title: "Error", text: data.message || "Something went wrong." });
        }
      })
      .catch(function () {
        Swal.fire({ icon: "error", title: "Error", text: "Something went wrong." });
      })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save Changes';
      });
  });
});
