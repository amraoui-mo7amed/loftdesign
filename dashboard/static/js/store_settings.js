document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("storeSettingsForm");
  if (!form) return;

  /* ── Color sync ── */
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

  /* ── Upload widget live preview ── */
  document.querySelectorAll(".upload-widget").forEach(function (widget) {
    var fileInput = widget.querySelector("input[type='file']");
    var preview = widget.querySelector(".upload-preview");
    var placeholder = widget.querySelector(".upload-placeholder");
    var removeBtn = widget.querySelector(".upload-remove");
    var hiddenRemove = widget.querySelector("input[type='hidden'][name^='remove_']");

    if (fileInput) {
      fileInput.addEventListener("change", function () {
        var file = this.files[0];
        if (!file) return;

        widget.classList.remove("supports-remove");
        widget.classList.add("has-file");

        if (preview) {
          var reader = new FileReader();
          reader.onload = function (e) {
            preview.src = e.target.result;
            preview.style.display = "block";
          };
          reader.readAsDataURL(file);
        }
        if (placeholder) placeholder.style.display = "none";
        if (hiddenRemove) hiddenRemove.value = "0";
      });
    }

    if (removeBtn) {
      removeBtn.addEventListener("click", function () {
        if (fileInput) fileInput.value = "";
        if (preview) { preview.src = ""; preview.style.display = "none"; }
        if (placeholder) placeholder.style.display = "";
        widget.classList.remove("has-file", "supports-remove");
        if (hiddenRemove) hiddenRemove.value = "1";
      });
    }
  });

  /* ── AJAX submit ── */
  var submitBtn = form.querySelector("button[type='submit']");
  var origBtnHtml = submitBtn ? submitBtn.innerHTML : "";

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Saving...';
    }

    var formData = new FormData(form);

    fetch(form.action, {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.success) {
          Swal.fire({
            icon: "success",
            title: "Saved",
            text: data.message,
            timer: 2000,
            showConfirmButton: false,
          }).then(function () { location.reload(); });
        } else {
          Swal.fire({ icon: "error", title: "Error", text: data.message || "Something went wrong." });
        }
      })
      .catch(function () {
        Swal.fire({ icon: "error", title: "Error", text: "Something went wrong." });
      })
      .finally(function () {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = origBtnHtml; }
      });
  });
});
