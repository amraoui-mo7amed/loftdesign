/**
 * LOFT Design — Product Create Page
 * Handles stepper, upload widgets, char counter, variant modal, AJAX submit.
 * Translatable strings come from data-* attributes on the form container.
 */
(function () {
  "use strict";

  var form = document.getElementById("portfolioForm");
  if (!form) return;

  var csrfToken = qs("[name=csrfmiddlewaretoken]").value;
  window.__savedVariants = [];

  // ── Read data attributes ────────────────────────────────
  var msgs = {
    unsupported: form.getAttribute("data-msg-unsupported") || ".{ext} not supported (use GLB/GLTF)",
    ready: form.getAttribute("data-msg-ready") || "{name} ready to upload",
    preparing: form.getAttribute("data-msg-preparing") || gettext("Preparing {name}..."),
    confirmRemove: form.getAttribute("data-msg-confirm-remove") || gettext("Remove this variant?"),
    newVariant: form.getAttribute("data-msg-new-variant") || gettext("New Variant"),
    editVariant: form.getAttribute("data-msg-edit-variant") || gettext("Edit Variant"),
    newVariantSub: form.getAttribute("data-msg-new-variant-sub") || gettext("Configure a product variant with its own media, color, dimensions, and stock."),
    editVariantSub: form.getAttribute("data-msg-edit-variant-sub") || gettext("Update the variant name, media, dimensions, or stock."),
  };

  // ── Helpers ─────────────────────────────────────────────
  function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
  function qsa(sel, ctx) { return (ctx || document).querySelectorAll(sel); }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  }

  // ── Upload Widget helper — prevents double file dialog ──
  function wireUploadWidget(widgetId, inputId) {
    var widget = document.getElementById(widgetId);
    var input = document.getElementById(inputId);
    if (!widget || !input) return;
    widget.addEventListener("click", function (e) {
      if (e.target.closest("input")) return;
      input.click();
    });
    return { widget: widget, input: input };
  }

  // ── Sticky Stepper ──────────────────────────────────────
  (function () {
    var wrap = document.getElementById("stepperWrap");
    var ph = null;
    var fixed = false;
    function update() {
      if (!wrap) return;
      var r = wrap.getBoundingClientRect();
      var should = r.top <= 0;
      if (should && !fixed) {
        fixed = true;
        wrap.classList.add("is-fixed");
        ph = document.createElement("div");
        ph.style.cssText = "width:" + r.width + "px;height:" + r.height + "px;margin-bottom:1rem;";
        wrap.parentNode.insertBefore(ph, wrap);
        wrap.style.cssText = "position:fixed;top:0;left:" + r.left + "px;width:" + r.width + "px;z-index:10;";
      } else if (!should && fixed) {
        fixed = false;
        wrap.classList.remove("is-fixed");
        wrap.style.cssText = "";
        if (ph) { ph.parentNode.removeChild(ph); ph = null; }
      }
    }
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", function () {
      if (fixed && wrap) {
        var r = wrap.getBoundingClientRect();
        if (ph) ph.style.width = r.width + "px";
        wrap.style.width = r.width + "px";
      }
    });
  })();

  // ── Description Counter ─────────────────────────────────
  (function () {
    var f = qs('textarea[name="description"]');
    var c = document.getElementById("descCounter");
    if (!f || !c) return;
    function upd() {
      var len = f.value.length;
      var max = f.getAttribute("maxlength") || 2000;
      c.textContent = len + " / " + max;
      c.className = "char-counter";
      if (len > max * 0.85) c.classList.add("warning");
      if (len > max * 0.95) c.classList.add("danger");
    }
    f.addEventListener("input", upd);
    upd();
  })();

  // ── Thumbnail Upload ────────────────────────────────────
  (function () {
    var w = wireUploadWidget("thumbWidget", "thumbInput");
    if (!w) return;
    var img = document.getElementById("thumbImg");
    var rm = document.getElementById("thumbRemove");
    w.input.addEventListener("change", function () {
      var f = this.files[0];
      if (!f) return;
      var r = new FileReader();
      r.onload = function (e) { img.src = e.target.result; img.style.display = "block"; w.widget.classList.add("has-file"); };
      r.readAsDataURL(f);
    });
    if (rm) {
      rm.addEventListener("click", function (e) {
        e.stopPropagation();
        w.input.value = ""; img.src = ""; img.style.display = "none"; w.widget.classList.remove("has-file");
      });
    }
  })();

  // ── Gallery Upload ──────────────────────────────────────
  (function () {
    var w = wireUploadWidget("galleryWidget", "galleryInput");
    if (!w) return;
    var preview = document.getElementById("galleryPreview");
    function render(files) {
      if (!preview) return;
      preview.innerHTML = "";
      Array.from(files).forEach(function (file, idx) {
        if (!file.type.startsWith("image/")) return;
        var r = new FileReader();
        r.onload = function (e) {
          var div = document.createElement("div");
          div.className = "preview-item";
          div.innerHTML = '<img src="' + e.target.result + '" alt="">' +
            '<span class="preview-remove" data-idx="' + idx + '">&times;</span>';
          preview.appendChild(div);
        };
        r.readAsDataURL(file);
      });
    }
    w.input.addEventListener("change", function () { render(this.files); });
    if (preview) {
      preview.addEventListener("click", function (e) {
        var btn = e.target.closest(".preview-remove");
        if (!btn) return;
        var idx = parseInt(btn.dataset.idx, 10);
        var dt = new DataTransfer();
        Array.from(w.input.files).forEach(function (f, i) { if (i !== idx) dt.items.add(f); });
        w.input.files = dt.files;
        render(w.input.files);
      });
    }
  })();

  // ── 3D Model Upload ─────────────────────────────────────
  (function () {
    var w = wireUploadWidget("modelWidget", "modelInput");
    if (!w) return;
    var statusText = document.getElementById("modelStatusText");
    var statusSize = document.getElementById("modelStatusSize");
    var statusBar = document.getElementById("modelStatusBar");
    var status = document.getElementById("modelStatus");
    w.input.addEventListener("change", function () {
      var file = this.files[0];
      if (!file) { if (status) status.classList.add("d-none"); return; }
      var ext = file.name.split(".").pop().toLowerCase();
      var isValid = ext === "glb" || ext === "gltf";
      if (status) status.classList.remove("d-none");
      if (statusBar) { statusBar.style.width = "0%"; statusBar.className = "progress-bar"; }
      if (!isValid) {
        if (statusBar) { statusBar.classList.add("bg-danger"); statusBar.style.width = "100%"; }
        if (statusText) statusText.textContent = msgs.unsupported.replace("{ext}", "." + ext);
        if (statusText) statusText.className = "fw-semibold text-danger";
        if (statusSize) statusSize.textContent = formatBytes(file.size);
        return;
      }
      if (statusText) statusText.textContent = msgs.preparing.replace("{name}", file.name);
      if (statusText) statusText.className = "fw-semibold text-primary";
      if (statusSize) statusSize.textContent = formatBytes(file.size);
      if (statusBar) statusBar.classList.add("progress-bar-striped", "progress-bar-animated");
      var pct = 0;
      var interval = setInterval(function () {
        pct += Math.floor(Math.random() * 15) + 5;
        if (pct >= 100) {
          pct = 100; clearInterval(interval);
          if (statusBar) { statusBar.className = "progress-bar bg-success"; statusBar.style.width = "100%"; }
          if (statusText) statusText.textContent = msgs.ready.replace("{name}", file.name);
          if (statusText) statusText.className = "fw-semibold text-success";
          if (statusSize) statusSize.textContent = formatBytes(file.size);
        }
        if (statusBar) statusBar.style.width = pct + "%";
      }, 200);
    });
  })();

  // ── Variant Modal ───────────────────────────────────────
  (function () {
    var modalEl = document.getElementById("variantModal");
    if (!modalEl) return;
    var modal = new bootstrap.Modal(modalEl);

    var container = document.getElementById("variantsContainer");
    var addBtn = document.getElementById("addVariantBtn");
    var saveBtn = document.getElementById("variantSaveBtn");

    // Modal form fields
    var mName = document.getElementById("varName");
    var mColorPicker = document.getElementById("varColorPicker");
    var mColorText = document.getElementById("varColorText");
    var mDimW = document.getElementById("varDimW");
    var mDimD = document.getElementById("varDimD");
    var mDimH = document.getElementById("varDimH");
    var mDimUnit = qs("input[name='varDimUnit']:checked") || document.getElementById("unitCm");
    var mStock = document.getElementById("varStock");
    var mThumbInput = document.getElementById("varThumbInput");
    var mGalleryInput = document.getElementById("varGalleryInput");
    var editingIndex = -1;

    // Modal preview elements
    var thumbPreview = document.getElementById("varThumbPreview");
    var thumbImg = document.getElementById("varThumbImg");
    var galleryPreview = document.getElementById("varGalleryPreview");

    function getEmptyText() {
      return container.getAttribute("data-empty-text") || gettext("No variants yet.");
    }

    function renderEmpty() {
      container.innerHTML =
        '<div class="variants-empty"><i class="fas fa-layer-group d-block"></i><p>' + getEmptyText() + "</p></div>";
      updateTotalStock();
    }

    function renderVariants() {
      container.innerHTML = "";
      if (!window.__savedVariants.length) { renderEmpty(); return; }
      window.__savedVariants.forEach(function (v, i) {
        var card = document.createElement("div");
        card.className = "variant-summary-card bg-light rounded-3 p-3 mb-3";
        card.style.cursor = "pointer";
        card.innerHTML =
          '<div class="d-flex align-items-center gap-3">' +
          (v.thumbnailUrl
            ? '<img src="' + v.thumbnailUrl + '" class="rounded-3" style="width:48px;height:48px;object-fit:cover;">'
            : '<div class="bg-white rounded-3 d-flex align-items-center justify-content-center" style="width:48px;height:48px;"><i class="fas fa-cube text-muted opacity-50"></i></div>') +
          '<div class="flex-grow-1 min-w-0">' +
          '<div class="fw-bold small text-truncate">' + escHtml(v.name) + '</div>' +
          '<div class="d-flex gap-2 flex-wrap small text-muted">' +
          (v.color ? '<span><i class="fas fa-palette me-1" style="font-size:0.6rem;"></i>' + escHtml(v.color) + '</span>' : '') +
          (v.dimensions ? '<span><i class="fas fa-ruler me-1" style="font-size:0.6rem;"></i>' + escHtml(v.dimensions) + '</span>' : '') +
          '<span><i class="fas fa-cubes me-1" style="font-size:0.6rem;"></i>' + v.stock + ' ' + (v.stock === 1 ? 'unit' : 'units') + '</span>' +
          (v.galleryCount ? '<span><i class="fas fa-images me-1" style="font-size:0.6rem;"></i>' + v.galleryCount + ' images</span>' : '') +
          '</div></div>' +
          '<button type="button" class="btn btn-sm btn-outline-danger rounded-circle flex-shrink-0 variant-remove-summary" data-idx="' + i + '" style="width:28px;height:28px;padding:0;" title="' + escHtml(msgs.confirmRemove) + '"><i class="fas fa-times"></i></button>' +
          '</div>';
        container.appendChild(card);

        // Click card body to edit
        card.addEventListener("click", function (e) {
          if (e.target.closest(".variant-remove-summary")) return;
          populateModal(i);
        });
      });
      // Attach remove handlers
      container.querySelectorAll(".variant-remove-summary").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var idx = parseInt(this.dataset.idx, 10);
          window.__savedVariants.splice(idx, 1);
          renderVariants();
        });
      });
      updateTotalStock();
    }

    function escHtml(s) {
      var d = document.createElement("div");
      d.appendChild(document.createTextNode(s || ""));
      return d.innerHTML;
    }

    function updateTotalStock() {
      var active = qs('input[name="is_active"]');
      var countEl = document.getElementById("variantCount");
      var total = window.__savedVariants.reduce(function (sum, v) { return sum + (parseInt(v.stock, 10) || 0); }, 0);
      if (countEl) { countEl.textContent = window.__savedVariants.length + " items"; }
      if (active) { active.checked = total > 0; }
    }

    function buildDimensions() {
      var w = (parseFloat(mDimW.value) || 0).toString();
      var d = (parseFloat(mDimD.value) || 0).toString();
      var h = (parseFloat(mDimH.value) || 0).toString();
      var unit = (qs("input[name='varDimUnit']:checked") || document.getElementById("unitCm")).value;
      if (!w && !d && !h) return "";
      return w + "×" + d + "×" + h + unit;
    }

    // Color picker ↔ text sync
    if (mColorPicker && mColorText) {
      mColorPicker.addEventListener("input", function () { if (!mColorText.value) mColorText.value = this.value; });
      mColorText.addEventListener("input", function () { if (/^#[0-9a-f]{6}$/i.test(this.value)) mColorPicker.value = this.value; });
    }

    // Click handlers for modal drop zones
    var thumbDrop = document.getElementById("varThumbDrop");
    var galleryDrop = document.getElementById("varGalleryDrop");

    if (thumbDrop && mThumbInput) {
      thumbDrop.addEventListener("click", function (e) {
        if (e.target.closest("input")) return;
        mThumbInput.click();
      });
    }

    if (galleryDrop && mGalleryInput) {
      galleryDrop.addEventListener("click", function (e) {
        if (e.target.closest("input")) return;
        mGalleryInput.click();
      });
    }

    // Thumbnail preview in modal
    if (mThumbInput && thumbImg && thumbPreview) {
      mThumbInput.addEventListener("change", function () {
        var f = this.files[0];
        if (!f) return;
        var r = new FileReader();
        r.onload = function (e) { thumbPreview.classList.add("d-none"); thumbImg.classList.remove("d-none"); thumbImg.src = e.target.result; };
        r.readAsDataURL(f);
      });
    }

    // Gallery preview in modal
    if (mGalleryInput && galleryPreview) {
      mGalleryInput.addEventListener("change", function () {
        galleryPreview.innerHTML = "";
        Array.from(this.files).forEach(function (file) {
          if (!file.type.startsWith("image/")) return;
          var r = new FileReader();
          r.onload = function (e) {
            var wrap = document.createElement("div");
            wrap.className = "position-relative";
            wrap.style.cssText = "width:60px;height:60px;";
            wrap.innerHTML =
              '<img src="' + e.target.result + '" class="rounded-3 w-100 h-100" style="object-fit:cover;">' +
              '<button type="button" class="btn btn-danger btn-sm position-absolute top-0 end-0 p-0 rounded-circle" style="width:18px;height:18px;font-size:8px;line-height:1;"><i class="fas fa-times"></i></button>';
            galleryPreview.appendChild(wrap);
          };
          r.readAsDataURL(file);
        });
      });
    }

    // Reset modal
    function resetModal() {
      editingIndex = -1;
      mName.value = "";
      if (mColorPicker) mColorPicker.value = "#6C757D";
      if (mColorText) mColorText.value = "";
      mDimW.value = ""; mDimD.value = ""; mDimH.value = "";
      document.getElementById("unitCm").checked = true;
      mStock.value = "0";
      mThumbInput.value = "";
      if (thumbPreview) thumbPreview.classList.remove("d-none");
      if (thumbImg) { thumbImg.classList.add("d-none"); thumbImg.src = ""; }
      mGalleryInput.value = "";
      if (galleryPreview) galleryPreview.innerHTML = "";
      var mh = modalEl.querySelector(".modal-header h5");
      var mp = modalEl.querySelector(".modal-header p");
      if (mh) mh.textContent = msgs.newVariant;
      if (mp) mp.textContent = msgs.newVariantSub;
    }

    function populateModal(idx) {
      var v = window.__savedVariants[idx];
      if (!v) return;
      editingIndex = idx;
      mName.value = v.name;
      if (mColorPicker) mColorPicker.value = v.color && /^#[0-9a-f]{6}$/i.test(v.color) ? v.color : "#6C757D";
      if (mColorText) mColorText.value = v.color || "";
      if (v.dimensions) {
        var parts = v.dimensions.match(/([\d.]+)×([\d.]+)×([\d.]+)(\w+)/);
        if (parts) {
          mDimW.value = parts[1]; mDimD.value = parts[2]; mDimH.value = parts[3];
          var unit = parts[4];
          var unitRadio = qs("input[name='varDimUnit'][value='" + unit + "']");
          if (unitRadio) unitRadio.checked = true;
        }
      }
      mStock.value = v.stock;
      if (v.thumbnailUrl && thumbImg && thumbPreview) {
        thumbPreview.classList.add("d-none");
        thumbImg.classList.remove("d-none");
        thumbImg.src = v.thumbnailUrl;
      }
      if (v.galleryFiles && v.galleryFiles.length && galleryPreview) {
        galleryPreview.innerHTML = "";
        v.galleryFiles.forEach(function (file) {
          if (!file.type || !file.type.startsWith("image/")) return;
          var r = new FileReader();
          r.onload = function (e) {
            var wrap = document.createElement("div");
            wrap.className = "position-relative";
            wrap.style.cssText = "width:60px;height:60px;";
            wrap.innerHTML = '<img src="' + e.target.result + '" class="rounded-3 w-100 h-100" style="object-fit:cover;">' +
              '<button type="button" class="btn btn-danger btn-sm position-absolute top-0 end-0 p-0 rounded-circle" style="width:18px;height:18px;font-size:8px;line-height:1;"><i class="fas fa-times"></i></button>';
            galleryPreview.appendChild(wrap);
          };
          r.readAsDataURL(file);
        });
      }
      var mh = modalEl.querySelector(".modal-header h5");
      var mp = modalEl.querySelector(".modal-header p");
      if (mh) mh.textContent = msgs.editVariant;
      if (mp) mp.textContent = msgs.editVariantSub;
      modal.show();
    }

    // Save variant from modal
    saveBtn.addEventListener("click", function () {
      var name = mName.value.trim();
      if (!name) { mName.focus(); return; }
      var color = mColorText ? mColorText.value.trim() : "";
      var dimensions = buildDimensions();
      var stock = parseInt(mStock.value, 10) || 0;
      var thumbFile = mThumbInput.files[0] || null;
      var galleryFiles = mGalleryInput.files ? Array.from(mGalleryInput.files) : [];
      var thumbnailUrl = null;
      if (thumbImg && !thumbImg.classList.contains("d-none")) thumbnailUrl = thumbImg.src;

      var variant = {
        name: name,
        color: color,
        dimensions: dimensions,
        stock: stock,
        thumbnailFile: thumbFile,
        galleryFiles: galleryFiles,
        thumbnailUrl: thumbnailUrl,
        galleryCount: galleryFiles.length,
      };

      if (editingIndex >= 0) {
        window.__savedVariants[editingIndex] = variant;
      } else {
        window.__savedVariants.push(variant);
      }

      renderVariants();
      modal.hide();
      resetModal();
    });

    // Open modal
    addBtn.addEventListener("click", function () { resetModal(); modal.show(); });

    // Init: show empty state
    renderEmpty();
  })();

  // ── AJAX Form Submission ────────────────────────────────
  var submitting = false;

  function doSubmit() {
    if (submitting) return;
    submitting = true;
    var btn = form.querySelector("button#submitProductBtn");
    if (!btn) return;
    btn.disabled = true;
    var originalHtml = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Submitting...';

    var fd = new FormData();

    // Collect standard form fields
    var standardFields = [
      "title", "category", "description", "tags", "external_link",
      "loft_purchase_price", "loft_wholesale_price", "loft_retail_price",
      "is_active", "is_featured",
    ];
    standardFields.forEach(function (name) {
      var el = qs('[name="' + name + '"]');
      if (el) {
        if (el.type === "checkbox") {
          if (el.checked) fd.append(name, "on");
        } else {
          fd.append(name, el.value);
        }
      }
    });

    // Thumbnail
    var thumbInput = document.getElementById("thumbInput");
    if (thumbInput && thumbInput.files[0]) fd.append("thumbnail", thumbInput.files[0]);

    // Gallery images
    var galleryInput = document.getElementById("galleryInput");
    if (galleryInput) {
      Array.from(galleryInput.files).forEach(function (f) { fd.append("gallery_images", f); });
    }

    // 3D model
    var modelInput = document.getElementById("modelInput");
    if (modelInput && modelInput.files[0]) fd.append("model_3d", modelInput.files[0]);

    // Variants from the global array
    (window.__savedVariants || []).forEach(function (v, i) {
      fd.append("items[" + i + "][name]", v.name);
      fd.append("items[" + i + "][color]", v.color || "");
      fd.append("items[" + i + "][dimensions]", v.dimensions || "");
      fd.append("items[" + i + "][stock_quantity]", v.stock);
      if (v.thumbnailFile) fd.append("items[" + i + "][thumbnail]", v.thumbnailFile);
      (v.galleryFiles || []).forEach(function (gf) {
        fd.append("items[" + i + "][gallery]", gf);
      });
    });

    fetch(form.action || window.location.href, {
      method: "POST",
      body: fd,
      headers: { "X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        submitting = false;
        btn.disabled = false;
        btn.innerHTML = originalHtml;
        if (data.success) {
          if (data.message) showToast(data.message, "success");
          if (data.redirect_url) { window.location.href = data.redirect_url; }
          else { window.location.href = "/dashboard/products/"; }
        } else {
          var errMsg = data.message || gettext("Error");
          if (data.errors) {
            var list = Object.values(data.errors).flat().join("<br>");
            errMsg = list;
          }
          showToast(errMsg, "danger");
        }
      })
      .catch(function (err) {
        submitting = false;
        btn.disabled = false;
        btn.innerHTML = originalHtml;
        showToast("Network error. Please try again.", "danger");
      });
  }

  document.getElementById("submitProductBtn").addEventListener("click", doSubmit);
  form.addEventListener("submit", function (e) { e.preventDefault(); doSubmit(); });

  // ── Toast notification ──────────────────────────────────
  function showToast(msg, type) {
    var container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.style.cssText = "position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;";
      document.body.appendChild(container);
    }
    var t = document.createElement("div");
    t.className = "alert alert-" + (type || "info") + " alert-dismissible fade show rounded-3 shadow-sm mb-0";
    t.style.cssText = "min-width:280px;max-width:400px;animation:slideIn 0.25s ease;";
    t.innerHTML = msg + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    container.appendChild(t);
    setTimeout(function () { t.remove(); }, 5000);
  }

  // ── Inject keyframes for toast animation ────────────────
  (function () {
    if (!document.getElementById("_createAnimStyle")) {
      var s = document.createElement("style");
      s.id = "_createAnimStyle";
      s.textContent = "@keyframes slideIn{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:translateX(0)}}";
      document.head.appendChild(s);
    }
  })();
})();
