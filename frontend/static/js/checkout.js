/**
 * LOFT Design - Checkout Page
 * Custom searchable dropdowns for Wilaya & Commune selection
 */

document.addEventListener("DOMContentLoaded", () => {
    const formEl = document.getElementById("checkoutForm");
    const communesDataEl = document.getElementById("communes-data");

    const l10n = formEl ? formEl.dataset : {
        selectWilayaFirst: "Please select a wilaya first",
        selectCommune: "Select Commune",
    };

    if (!communesDataEl) return;

    const communesData = JSON.parse(communesDataEl.textContent);

    // ── Searchable Select Component ────────────────────────────────
    function createSearchableSelect(containerId, onChange) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        const display = container.querySelector(".searchable-select-display");
        const selectedText = container.querySelector(".selected-text");
        const dropdown = container.querySelector(".searchable-select-dropdown");
        const searchInput = container.querySelector(".search-input");
        const hiddenInput = container.querySelector('input[type="hidden"]');
        const list = container.querySelector(".searchable-select-list");

        const close = () => dropdown.classList.remove("show");

        display.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = dropdown.classList.contains("show");
            document.querySelectorAll(".searchable-select-dropdown.show").forEach((d) => d.classList.remove("show"));
            if (!isOpen) {
                dropdown.classList.add("show");
                searchInput.focus();
            }
        });

        searchInput.addEventListener("input", () => {
            const term = searchInput.value.trim().toLowerCase();
            list.querySelectorAll("li").forEach((item) => {
                item.classList.toggle("d-none", !item.textContent.toLowerCase().includes(term));
            });
        });

        list.addEventListener("click", (e) => {
            const item = e.target.closest("li");
            if (!item) return;
            e.stopPropagation();

            list.querySelectorAll("li").forEach((i) => i.classList.remove("selected"));
            item.classList.add("selected");
            selectedText.textContent = item.textContent;
            hiddenInput.value = item.dataset.value;
            close();

            if (onChange) onChange(item.dataset.value);
        });

        document.addEventListener("click", close);
        return { container, close };
    }

    // ── Wilaya → Communes ─────────────────────────────────────────
    const communeList = document.querySelector("#commune-searchable .searchable-select-list");
    const communeSelectedText = document.querySelector("#commune-searchable .selected-text");
    const communeHiddenInput = document.querySelector('#commune-searchable input[type="hidden"]');
    const communeSearchInput = document.querySelector("#commune-searchable .search-input");

    function updateCommunes(wilayaId) {
        communeList.innerHTML = "";
        communeSelectedText.textContent = l10n.selectCommune;
        communeHiddenInput.value = "";
        communeSearchInput.value = "";

        const options = communesData[wilayaId];
        if (!options) return;

        options.forEach((opt) => {
            const li = document.createElement("li");
            li.setAttribute("data-value", opt.value);
            li.textContent = opt.label;
            communeList.appendChild(li);
        });
    }

    createSearchableSelect("wilaya-searchable", updateCommunes);
    createSearchableSelect("commune-searchable");

    // Prefilled after a validation error: show the chosen wilaya / commune again.
    const wilayaHidden = document.querySelector('#wilaya-searchable input[type="hidden"]');
    if (wilayaHidden && wilayaHidden.value) {
        const chosen = document.querySelector('#wilaya-searchable li[data-value="' + CSS.escape(wilayaHidden.value) + '"]');
        if (chosen) document.querySelector("#wilaya-searchable .selected-text").textContent = chosen.textContent;
        const keepCommune = communeHiddenInput.value;
        updateCommunes(wilayaHidden.value);
        const c = keepCommune && communeList.querySelector('li[data-value="' + CSS.escape(keepCommune) + '"]');
        if (c) { communeHiddenInput.value = keepCommune; communeSelectedText.textContent = c.textContent; }
    }

    // Hidden inputs are not checked by the browser: check wilaya / commune here.
    if (formEl) {
        formEl.addEventListener("submit", (e) => {
            [["wilaya-searchable", gettext("Please choose your wilaya")], ["commune-searchable", gettext("Please choose your commune")]].forEach(([id, msg]) => {
                const wrap = document.getElementById(id);
                const hidden = wrap && wrap.querySelector('input[type="hidden"]');
                if (!hidden || hidden.value || e.defaultPrevented) return;
                e.preventDefault();
                wrap.classList.add("is-invalid");
                wrap.scrollIntoView({ behavior: "smooth", block: "center" });
                if (window.Swal) Swal.fire({ icon: "warning", title: msg, confirmButtonColor: "#212121" });
                else alert(msg);
            });
        });
    }
});
