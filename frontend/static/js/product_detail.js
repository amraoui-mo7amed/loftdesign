/**
 * LOFT Design - Product Detail Page
 * Handles dynamic location selection for orders
 */

document.addEventListener('DOMContentLoaded', () => {
    const communesDataEl = document.getElementById('communes-data');
    if (!communesDataEl) return;

    const communesData = JSON.parse(communesDataEl.textContent);
    const wilayaInput = document.querySelector('#wilayaSelect_input');
    const communeContainer = document.getElementById('communeSelectContainer');
    
    // Listen for changes on the hidden input of the custom select
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'attributes' && mutation.attributeName === 'value') {
                const wilayaId = wilayaInput.value;
                updateCommunes(wilayaId);
            }
        });
    });

    if (wilayaInput) {
        observer.observe(wilayaInput, { attributes: true });
    }

    function updateCommunes(wilayaId) {
        if (!wilayaId || !communesData[wilayaId]) {
            communeContainer.innerHTML = `<div class="alert alert-light border small py-2 mb-0">${window.L10N_STRINGS.selectWilayaFirst}</div>`;
            return;
        }

        const options = communesData[wilayaId];
        let listHtml = options.map(opt => `<li data-value="${opt.value}">${opt.label}</li>`).join('');
        
        communeContainer.innerHTML = `
            <div class="custom-select-wrapper full-width" id="communeSelect">
                <div class="custom-select-display">
                    <span class="selected-text">${window.L10N_STRINGS.selectCommune}</span>
                    <span class="arrow"><i class="fas fa-caret-down"></i></span>
                </div>
                <ul class="custom-select-list">${listHtml}</ul>
                <input type="hidden" id="communeSelect_input" name="commune" value="" required />
            </div>
        `;

        attachCustomSelectLogic(communeContainer.querySelector('.custom-select-wrapper'));
    }

    function attachCustomSelectLogic(wrapper) {
        const display = wrapper.querySelector('.custom-select-display');
        const list = wrapper.querySelector('.custom-select-list');
        const hiddenInput = wrapper.querySelector('input[type="hidden"]');

        display.addEventListener('click', (e) => {
            e.stopPropagation();
            list.classList.toggle('show');
            display.classList.toggle('active');
            wrapper.classList.toggle('active');
        });

        list.querySelectorAll('li').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const selectedText = item.textContent;
                hiddenInput.value = item.dataset.value;
                list.classList.remove('show');
                display.classList.remove('active');
                wrapper.classList.remove('active');
                display.innerHTML = `${selectedText} <span class="arrow"><i class="fas fa-caret-down"></i></span>`;
            });
        });
    }
});
