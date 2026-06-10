document.addEventListener("DOMContentLoaded", () => {
  const modelInput = document.querySelector('input[name="model_3d"]');
  const modelStatus = document.getElementById("modelStatus");
  const modelStatusText = document.getElementById("modelStatusText");
  const modelStatusSize = document.getElementById("modelStatusSize");
  const modelStatusBar = document.getElementById("modelStatusBar");

  const formatBytes = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  };

  if (!modelInput || !modelStatus) return;

  let uploadXHR = null;

  modelInput.addEventListener("change", function () {
    const file = this.files[0];
    if (!file) {
      modelStatus.classList.add("d-none");
      return;
    }

    const ext = file.name.split(".").pop().toLowerCase();
    const isValid = ext === "glb" || ext === "gltf";

    modelStatus.classList.remove("d-none");
    modelStatusBar.style.width = "0%";
    modelStatusBar.className = "progress-bar";

    if (!isValid) {
      modelStatusBar.classList.add("bg-danger");
      modelStatusBar.style.width = "100%";
      modelStatusText.textContent = "\u2717 ." + ext + " not supported (use GLB/GLTF)";
      modelStatusText.className = "fw-semibold text-danger";
      modelStatusSize.textContent = formatBytes(file.size);
      return;
    }

    modelStatusText.textContent = "Preparing " + file.name + "...";
    modelStatusText.className = "fw-semibold text-primary";
    modelStatusSize.textContent = formatBytes(file.size);
    modelStatusBar.classList.add("progress-bar-striped", "progress-bar-animated");

    let pct = 0;
    const interval = setInterval(() => {
      pct += Math.floor(Math.random() * 15) + 5;
      if (pct >= 100) {
        pct = 100;
        clearInterval(interval);
        modelStatusBar.className = "progress-bar bg-success";
        modelStatusBar.style.width = "100%";
        modelStatusText.textContent = "\u2713 " + file.name + " ready to upload";
        modelStatusText.className = "fw-semibold text-success";
        modelStatusSize.textContent = formatBytes(file.size);
      }
      modelStatusBar.style.width = pct + "%";
    }, 200);
  });

  const form = document.getElementById("portfolioForm");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    const file = modelInput && modelInput.files[0];
    if (!file) return;

    const ext = file.name.split(".").pop().toLowerCase();
    if (ext !== "glb" && ext !== "gltf") {
      e.preventDefault();
      return;
    }

    e.preventDefault();

    const btn = this.querySelector('button[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span> ' +
        (btn.textContent.trim() || "Uploading...");
    }

    modelStatus.classList.remove("d-none");
    modelStatusBar.className = "progress-bar progress-bar-striped progress-bar-animated";
    modelStatusBar.style.width = "0%";
    modelStatusText.textContent = "Uploading " + file.name + "...";
    modelStatusText.className = "fw-semibold text-primary";
    modelStatusSize.textContent = "0%";

    const xhr = new XMLHttpRequest();
    uploadXHR = xhr;
    const fd = new FormData(this);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        modelStatusBar.style.width = pct + "%";
        modelStatusSize.textContent = pct + "%";
      }
    });

    xhr.addEventListener("load", function () {
      uploadXHR = null;
      if (xhr.status >= 200 && xhr.status < 300) {
        modelStatusBar.className = "progress-bar bg-success";
        modelStatusBar.style.width = "100%";
        modelStatusText.textContent = "\u2713 " + file.name + " uploaded";
        modelStatusText.className = "fw-semibold text-success";
        modelStatusSize.textContent = "100%";
        try {
          const data = JSON.parse(xhr.responseText);
          if (data.redirect_url) {
            window.location.href = data.redirect_url;
          } else if (data.success) {
            window.location.href = ".";
          }
        } catch {
          window.location.href = ".";
        }
      } else {
        modelStatusBar.className = "progress-bar bg-danger";
        modelStatusText.textContent = "\u2717 Upload failed";
        modelStatusText.className = "fw-semibold text-danger";
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i class="fas fa-plus-circle me-2"></i> Retry';
        }
      }
    });

    xhr.addEventListener("error", function () {
      uploadXHR = null;
      modelStatusBar.className = "progress-bar bg-danger";
      modelStatusText.textContent = "\u2717 Network error";
      modelStatusText.className = "fw-semibold text-danger";
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-plus-circle me-2"></i> Retry';
      }
    });

    xhr.open("POST", this.action);
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    const csrf = this.querySelector('[name="csrfmiddlewaretoken"]');
    if (csrf) xhr.setRequestHeader("X-CSRFToken", csrf.value);
    xhr.send(fd);
  });
});
