/**
 * LOFT Design - Product Detail Page
 * Handles custom searchable dropdowns for locations
 */

document.addEventListener('DOMContentLoaded', () => {
    const communesDataEl = document.getElementById('communes-data');
    if (!communesDataEl) return;

    const communesData = JSON.parse(communesDataEl.textContent);
    
    // Initialize Wilaya Select
    initSearchableSelect('wilaya-searchable', (value) => {
        updateCommunes(value);
    });

    // Initialize Commune Select (empty initially)
    initSearchableSelect('commune-searchable');

    function updateCommunes(wilayaId) {
        const list = document.querySelector('#commune-searchable .searchable-select-list');
        const display = document.querySelector('#commune-searchable .selected-text');
        const hiddenInput = document.querySelector('#commune-searchable input[type="hidden"]');
        
        // Reset state
        list.innerHTML = '';
        display.textContent = window.L10N_STRINGS.selectCommune;
        hiddenInput.value = '';

        if (!wilayaId || !communesData[wilayaId]) {
            return;
        }

        const options = communesData[wilayaId];
        options.forEach(opt => {
            const li = document.createElement('li');
            li.setAttribute('data-value', opt.value);
            li.textContent = opt.label;
            list.appendChild(li);
        });

        // Re-bind listeners for the new list items
        bindListItems('commune-searchable');
    }

    function initSearchableSelect(containerId, onChange) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const display = container.querySelector('.searchable-select-display');
        const dropdown = container.querySelector('.searchable-select-dropdown');
        const searchInput = container.querySelector('.search-input');
        
        display.addEventListener('click', (e) => {
            e.stopPropagation();
            // Close other dropdowns
            document.querySelectorAll('.searchable-select-dropdown.show').forEach(d => {
                if (d !== dropdown) d.classList.remove('show');
            });
            dropdown.classList.toggle('show');
            if (dropdown.classList.contains('show')) {
                searchInput.focus();
            }
        });

        searchInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            const items = container.querySelectorAll('.searchable-select-list li');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.classList.toggle('d-none', !text.includes(term));
            });
        });

        bindListItems(containerId, onChange);

        document.addEventListener('click', () => {
            dropdown.classList.remove('show');
        });
    }

    function bindListItems(containerId, onChange) {
        const container = document.getElementById(containerId);
        const display = container.querySelector('.selected-text');
        const hiddenInput = container.querySelector('input[type="hidden"]');
        const dropdown = container.querySelector('.searchable-select-dropdown');
        const items = container.querySelectorAll('.searchable-select-list li');

        items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const value = item.getAttribute('data-value');
                const text = item.textContent;

                // Update UI
                items.forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                display.textContent = text;
                hiddenInput.value = value;
                
                dropdown.classList.remove('show');

                if (onChange) onChange(value);
            });
        });
    }
});
