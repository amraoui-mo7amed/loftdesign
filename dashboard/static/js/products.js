document.addEventListener("DOMContentLoaded", () => {
  var modelInput = document.querySelector('input[name="model_3d"]');
  var modelStatus = document.getElementById("modelStatus");
  var modelStatusText = document.getElementById("modelStatusText");
  var modelStatusSize = document.getElementById("modelStatusSize");
  var modelStatusBar = document.getElementById("modelStatusBar");

  if (!modelInput || !modelStatus) return;

  var formatBytes = function (bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  };

  modelInput.addEventListener("change", function () {
    var file = this.files[0];
    if (!file) {
      modelStatus.classList.add("d-none");
      return;
    }

    var ext = file.name.split(".").pop().toLowerCase();
    var isValid = ext === "glb" || ext === "gltf";

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

    var pct = 0;
    var interval = setInterval(function () {
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
});
