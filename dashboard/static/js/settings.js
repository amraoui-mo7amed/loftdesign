/**
 * LOFT Design - Global Settings JS
 * Handles dynamic dynamic slider additions and deletions in the grid view
 */

document.addEventListener('DOMContentLoaded', () => {
    const gridContainer = document.getElementById('sliderGridContainer');
    const additionsContainer = document.getElementById('additionsContainer');
    const deletionsContainer = document.getElementById('deletionsContainer');
    let newItemCounter = 0;

    // Handle dynamically adding upload cards on click of the upload zone
    const initUploadZone = (zone) => {
        zone.addEventListener('click', () => {
            newItemCounter++;
            const inputId = `new_slider_image_${newItemCounter}`;
            
            // Create hidden file input inside additions container
            const input = document.createElement('input');
            input.type = 'file';
            input.name = 'new_slider_image';
            input.accept = 'image/*';
            input.className = 'd-none';
            input.id = inputId;
            additionsContainer.appendChild(input);

            input.click();

            input.addEventListener('change', function() {
                const file = this.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        // Create a card preview inside the grid
                        const card = document.createElement('div');
                        card.className = 'settings-image-card reveal reveal-up';
                        card.id = `card-new-${newItemCounter}`;
                        card.innerHTML = `
                            <div class="card-preview">
                                <img src="${e.target.result}">
                                <div class="hover-delete-overlay rounded-3" onclick="document.getElementById('card-new-${newItemCounter}').remove(); document.getElementById('${inputId}').remove();">
                                    <i class="fas fa-trash fa-lg"></i>
                                    <span>Delete</span>
                                </div>
                            </div>
                        `;
                        // Insert card right before the upload zone
                        gridContainer.insertBefore(card, zone);
                    };
                    reader.readAsDataURL(file);
                } else {
                    input.remove(); // Cleanup if cancelled
                }
            });
        });
    };

    const mainUploadZone = document.getElementById('mainUploadZone');
    if (mainUploadZone) initUploadZone(mainUploadZone);

    // Handle existing image removal
    document.querySelectorAll('.hover-delete-overlay[data-id]').forEach(overlay => {
        overlay.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            const card = document.getElementById(`card-existing-${id}`);
            if (card) {
                card.remove();
                const deletionInput = document.createElement('input');
                deletionInput.type = 'hidden';
                deletionInput.name = 'delete_slider_image';
                deletionInput.value = id;
                deletionsContainer.appendChild(deletionInput);
            }
        });
    });
});
