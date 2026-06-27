document.addEventListener("DOMContentLoaded", function () {
    var productId = document.querySelector("[data-product-id]");
    if (!productId) return;
    var pk = productId.dataset.productId;

    // ── Image Previews ──────────────────────────────────────────────
    var thumbDrop = document.getElementById("itemThumbDrop");
    var thumbInput = document.getElementById("itemThumbnailInput");
    var thumbPreview = document.getElementById("itemThumbPreview");
    var thumbImg = document.getElementById("itemThumbImg");

    if (thumbDrop && thumbInput) {
        thumbDrop.addEventListener("click", function () { thumbInput.click(); });
        thumbDrop.addEventListener("dragover", function (e) { e.preventDefault(); this.classList.add("dragover"); });
        thumbDrop.addEventListener("dragleave", function () { this.classList.remove("dragover"); });
        thumbDrop.addEventListener("drop", function (e) {
            e.preventDefault();
            this.classList.remove("dragover");
            if (e.dataTransfer.files.length) {
                thumbInput.files = e.dataTransfer.files;
                thumbInput.dispatchEvent(new Event("change"));
            }
        });
        thumbInput.addEventListener("change", function () {
            var file = this.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    thumbPreview.classList.add("d-none");
                    thumbImg.classList.remove("d-none");
                    thumbImg.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    var galleryDrop = document.getElementById("itemGalleryDrop");
    var galleryInput = document.getElementById("itemGalleryInput");
    var galleryPreview = document.getElementById("itemGalleryPreview");

    if (galleryDrop && galleryInput) {
        galleryDrop.addEventListener("click", function () { galleryInput.click(); });
        galleryDrop.addEventListener("dragover", function (e) { e.preventDefault(); this.classList.add("dragover"); });
        galleryDrop.addEventListener("dragleave", function () { this.classList.remove("dragover"); });
        galleryDrop.addEventListener("drop", function (e) {
            e.preventDefault();
            this.classList.remove("dragover");
            if (e.dataTransfer.files.length) {
                galleryInput.files = e.dataTransfer.files;
                galleryInput.dispatchEvent(new Event("change"));
            }
        });
        galleryInput.addEventListener("change", function () {
            galleryPreview.innerHTML = "";
            Array.from(this.files).forEach(function (file) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    var wrap = document.createElement("div");
                    wrap.className = "position-relative";
                    wrap.style.width = "72px";
                    wrap.style.height = "72px";
                    var img = document.createElement("img");
                    img.src = e.target.result;
                    img.className = "rounded-3 w-100 h-100";
                    img.style.objectFit = "cover";
                    var removeBtn = document.createElement("button");
                    removeBtn.type = "button";
                    removeBtn.className = "btn btn-danger btn-sm position-absolute top-0 end-0 p-0 rounded-circle";
                    removeBtn.style.width = "20px";
                    removeBtn.style.height = "20px";
                    removeBtn.style.fontSize = "10px";
                    removeBtn.style.lineHeight = "1";
                    removeBtn.innerHTML = '<i class="fas fa-times"></i>';
                    removeBtn.addEventListener("click", function () {
                        wrap.remove();
                        var dt = new DataTransfer();
                        var files = galleryInput.files;
                        for (var i = 0; i < files.length; i++) {
                            if (files[i] !== file) dt.items.add(files[i]);
                        }
                        galleryInput.files = dt.files;
                    });
                    wrap.appendChild(img);
                    wrap.appendChild(removeBtn);
                    galleryPreview.appendChild(wrap);
                };
                reader.readAsDataURL(file);
            });
        });
    }

    // ── Color Picker ↔ Text Sync ───────────────────────────────────
    var colorInput = document.getElementById("itemColorInput");
    var colorText = document.getElementById("itemColorText");
    if (colorInput && colorText) {
        colorInput.addEventListener("input", function () {
            if (!colorText.value) colorText.value = this.value;
        });
        colorText.addEventListener("input", function () {
            // no reverse sync needed — keeps hex as fallback name
        });
    }

    // ── Dimension Builder ──────────────────────────────────────────
    var dimW = document.getElementById("dimWidth");
    var dimD = document.getElementById("dimDepth");
    var dimH = document.getElementById("dimHeight");
    var dimRadios = document.querySelectorAll('input[name="dimUnit"]');
    var dimHidden = document.getElementById("itemDimensionsInput");

    function getDimUnit() {
        var checked = document.querySelector('input[name="dimUnit"]:checked');
        return checked ? checked.value : "cm";
    }

    function setDimUnit(val) {
        var radio = document.querySelector('input[name="dimUnit"][value="' + val + '"]');
        if (radio) radio.checked = true;
    }

    function buildDimensions() {
        var parts = [];
        var w = dimW ? dimW.value.trim() : "";
        var d = dimD ? dimD.value.trim() : "";
        var h = dimH ? dimH.value.trim() : "";
        var u = getDimUnit();
        if (w || d || h) {
            if (w) parts.push(w);
            if (d) parts.push(d);
            if (h) parts.push(h);
            dimHidden.value = parts.join("x") + " " + u;
        } else {
            dimHidden.value = "";
        }
    }

    [dimW, dimD, dimH].forEach(function (el) {
        if (el) el.addEventListener("input", buildDimensions);
    });
    dimRadios.forEach(function (el) {
        if (el) el.addEventListener("change", buildDimensions);
    });

    function parseDimensions(str) {
        if (!str) return;
        var match = str.match(/^([\d.]+)x([\d.]+)x([\d.]+)\s*(mm|cm|m)$/);
        if (match) {
            if (dimW) dimW.value = match[1];
            if (dimD) dimD.value = match[2];
            if (dimH) dimH.value = match[3];
            setDimUnit(match[4]);
        } else {
            var m2 = str.match(/^([\d.]+)x([\d.]+)\s*(mm|cm|m)$/);
            if (m2) {
                if (dimW) dimW.value = m2[1];
                if (dimD) dimD.value = m2[2];
                setDimUnit(m2[3]);
            }
        }
    }

    // ── Load Items ──────────────────────────────────────────────────
    function loadItems() {
        fetch("/dashboard/products/" + pk + "/items/")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) renderItems(data.items);
            });
    }

    function renderItems(items) {
        var container = document.getElementById("itemsContainer");
        if (!container) return;
        if (!items || items.length === 0) {
            container.innerHTML =
                '<div class="text-center py-4" id="noItemsPlaceholder">' +
                '<i class="fas fa-box-open fa-3x text-muted opacity-25 mb-3"></i>' +
                '<p class="text-muted mb-0">' + (container.dataset.emptyText || "No items yet.") + '</p>' +
                "</div>";
            return;
        }
        var html =
            '<div class="table-responsive"><table class="table align-middle mb-0">' +
            '<thead class="table-light"><tr>' +
            '<th style="width: 60px;">Image</th><th>Name</th><th>Color</th><th>Dimensions</th>' +
            '<th class="text-center">Stock</th><th class="text-end">Actions</th>' +
            "</tr></thead><tbody>";
        items.forEach(function (item) {
            var thumbHtml = item.thumbnail
                ? '<img src="' + item.thumbnail + '" alt="' + item.name + '" class="rounded-3" style="width:50px;height:50px;object-fit:cover;">'
                : '<div class="bg-light rounded-3 d-flex align-items-center justify-content-center" style="width:50px;height:50px;"><i class="fas fa-box text-muted opacity-50"></i></div>';
            var colorHtml = item.color
                ? '<span class="d-inline-block rounded-circle me-1" style="width:14px;height:14px;background:' + item.color.toLowerCase() + ';vertical-align:middle;"></span> ' + item.color
                : '<span class="text-muted small">&mdash;</span>';
            var stockBadge = item.stock_quantity > 0
                ? '<span class="badge bg-success-subtle text-success rounded-pill px-3">' + item.stock_quantity + "</span>"
                : '<span class="badge bg-danger-subtle text-danger rounded-pill px-3">' + item.stock_quantity + "</span>";
            html +=
                '<tr data-item-id="' + item.id + '">' +
                "<td>" + thumbHtml + "</td>" +
                '<td class="fw-bold">' + item.name + "</td>" +
                "<td>" + colorHtml + "</td>" +
                '<td class="small text-muted">' + (item.dimensions || "&mdash;") + "</td>" +
                '<td class="text-center">' + stockBadge + "</td>" +
                '<td class="text-end">' +
                '<button type="button" class="btn btn-sm btn-outline-primary rounded-pill edit-item-btn me-1" data-item-id="' + item.id + '"><i class="fas fa-edit"></i></button>' +
                '<button type="button" class="btn btn-sm btn-outline-danger rounded-pill delete-item-btn" data-item-id="' + item.id + '" data-item-name="' + item.name + '"><i class="fas fa-trash-alt"></i></button>' +
                "</td></tr>";
        });
        html += "</tbody></table></div>";
        container.innerHTML = html;
        attachItemEvents();
    }

    function attachItemEvents() {
        document.querySelectorAll(".edit-item-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                openEditModal(this.dataset.itemId);
            });
        });
        document.querySelectorAll(".delete-item-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                confirmDeleteItem(this.dataset.itemId, this.dataset.itemName);
            });
        });
    }

    // ── Open Create Modal ───────────────────────────────────────────
    document.getElementById("addItemBtn").addEventListener("click", function () {
        resetModal();
        document.getElementById("itemFormModalLabel").textContent = "Add Item";
        document.getElementById("itemFormSubmitText").textContent = "Save Item";
        document.getElementById("itemForm").action = "/dashboard/products/" + pk + "/items/create/";
        var thumbInput = document.getElementById("itemThumbnailInput");
        if (thumbInput) thumbInput.required = true;
    });

    // ── Open Edit Modal ─────────────────────────────────────────────
    function openEditModal(itemId) {
        fetch("/dashboard/products/" + pk + "/items/")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    var found = data.items.find(function (i) { return i.id == itemId; });
                    if (found) populateEditModal(found);
                }
            });
    }

    function populateEditModal(data) {
        resetModal();
        document.getElementById("itemFormModalLabel").textContent = "Edit Item";
        document.getElementById("itemFormSubmitText").textContent = "Update Item";
        document.getElementById("itemForm").action = "/dashboard/items/" + data.id + "/update/";
        document.getElementById("itemIdInput").value = data.id;
        document.getElementById("itemNameInput").value = data.name;

        // Color
        if (data.color) {
            var isHex = /^#[0-9a-f]{3,6}$/i.test(data.color);
            if (isHex) {
                colorInput.value = data.color;
                colorText.value = "";
            } else {
                colorInput.value = "#808080";
                colorText.value = data.color;
            }
        }

        // Dimensions
        parseDimensions(data.dimensions);

        // Stock
        document.getElementById("itemStockInput").value = data.stock_quantity;

        // Thumbnail preview
        if (data.thumbnail) {
            thumbPreview.classList.add("d-none");
            thumbImg.classList.remove("d-none");
            thumbImg.src = data.thumbnail;
        }

        // Gallery images
        var galleryContainer = document.getElementById("itemGalleryPreview");
        galleryContainer.innerHTML = "";
        if (data.gallery_images) {
            data.gallery_images.forEach(function (img) {
                var wrap = document.createElement("div");
                wrap.className = "position-relative";
                wrap.style.width = "72px";
                wrap.style.height = "72px";
                var el = document.createElement("img");
                el.src = img.url;
                el.className = "rounded-3 w-100 h-100";
                el.style.objectFit = "cover";
                wrap.appendChild(el);
                galleryContainer.appendChild(wrap);
            });
        }

        var thumbInput = document.getElementById("itemThumbnailInput");
        if (thumbInput) thumbInput.required = false;

        var modal = new bootstrap.Modal(document.getElementById("itemFormModal"));
        modal.show();
    }

    // ── Reset Modal ─────────────────────────────────────────────────
    function resetModal() {
        document.getElementById("itemForm").reset();
        document.getElementById("itemIdInput").value = "";
        document.getElementById("itemDimensionsInput").value = "";
        thumbPreview.classList.remove("d-none");
        thumbImg.classList.add("d-none");
        thumbImg.src = "";
        document.getElementById("itemGalleryPreview").innerHTML = "";
        [dimW, dimD, dimH].forEach(function (el) { if (el) el.value = ""; });
        setDimUnit("cm");
        if (colorInput) colorInput.value = "#808080";
        if (colorText) colorText.value = "";
        var ec = document.querySelector("#itemForm #errorContainer");
        if (ec) ec.classList.add("d-none");
    }

    // ── Confirm Delete ──────────────────────────────────────────────
    function confirmDeleteItem(itemId, itemName) {
        var swalTitle = document.querySelector("[data-swal-title]");
        var swalText = document.querySelector("[data-swal-text]");
        var swalConfirm = document.querySelector("[data-swal-confirm]");
        var swalCancel = document.querySelector("[data-swal-cancel]");
        Swal.fire({
            title: swalTitle ? swalTitle.dataset.swalTitle : "Remove Item?",
            text: (swalText ? swalText.dataset.swalText : "Are you sure you want to remove") + " '" + itemName + "'?",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: swalConfirm ? swalConfirm.dataset.swalConfirm : "Yes, remove",
            cancelButtonText: swalCancel ? swalCancel.dataset.swalCancel : "Cancel",
            confirmButtonColor: "#dc3545",
        }).then(function (result) {
            if (result.isConfirmed) {
                fetch("/dashboard/items/" + itemId + "/delete/", {
                    method: "POST",
                    headers: { "X-CSRFToken": getCSRFToken(), "X-Requested-With": "XMLHttpRequest" }
                })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) {
                        Swal.fire({ icon: "success", title: "Removed!", timer: 1500, showConfirmButton: false });
                        loadItems();
                    }
                });
            }
        });
    }

    // ── Form Submit (AJAX) ──────────────────────────────────────────
    var submitting = false;
    document.getElementById("itemForm").addEventListener("submit", function (e) {
        if (!this.checkValidity()) return;
        e.preventDefault();
        if (submitting) return;
        submitting = true;

        var form = this;
        var submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        var formData = new FormData(form);

        // Build dimension string before submission
        buildDimensions();

        // Append color text
        if (colorText && colorText.value.trim()) {
            formData.set("color", colorText.value.trim());
        } else if (colorInput) {
            formData.set("color", colorInput.value);
        }

        var errorContainer = form.querySelector("#errorContainer");

        fetch(form.action, {
            method: "POST",
            body: formData,
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            submitting = false;
            if (submitBtn) submitBtn.disabled = false;
            if (data.success) {
                var modal = bootstrap.Modal.getInstance(document.getElementById("itemFormModal"));
                if (modal) modal.hide();
                Swal.fire({ icon: "success", title: data.message || "Saved!", timer: 1500, showConfirmButton: false });
                loadItems();
                resetModal();
            } else {
                var list = errorContainer ? errorContainer.querySelector("ul") : null;
                if (list && data.errors) {
                    list.innerHTML = "";
                    for (var key in data.errors) {
                        data.errors[key].forEach(function (m) {
                            var li = document.createElement("li");
                            li.textContent = m;
                            list.appendChild(li);
                        });
                    }
                    errorContainer.classList.remove("d-none");
                }
            }
        });
    });

    // ── Helper: CSRF Token ──────────────────────────────────────────
    function getCSRFToken() {
        var csrf = document.querySelector("[name=csrfmiddlewaretoken]");
        return csrf ? csrf.value : "";
    }
});
