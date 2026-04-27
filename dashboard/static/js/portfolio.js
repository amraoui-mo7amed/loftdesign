/**
 * LOFT Design - Portfolio Management JS
 * Handles previews, drag & drop, and form animations
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Thumbnail Preview
    const thumbInput = document.querySelector('input[name="thumbnail"]');
    const thumbPreviewContainer = document.getElementById('thumbPreviewContainer');
    
    if (thumbInput) {
        thumbInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    thumbPreviewContainer.innerHTML = `
                        <div class="preview-item w-100 mb-0" style="aspect-ratio: 16/9;">
                            <img src="${e.target.result}" alt="Thumbnail Preview">
                        </div>
                    `;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 2. Gallery Preview (Multi-file)
    const galleryInput = document.querySelector('input[name="gallery_images"]');
    const galleryPreviewContainer = document.getElementById('galleryPreviewContainer');
    
    if (galleryInput) {
        galleryInput.addEventListener('change', function() {
            // Clear previous previews for new uploads
            galleryPreviewContainer.innerHTML = '';
            
            const files = Array.from(this.files);
            files.forEach((file, index) => {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const item = document.createElement('div');
                        item.className = 'preview-item';
                        item.innerHTML = `
                            <img src="${e.target.result}" alt="Preview ${index}">
                            <div class="preview-info">
                                ${ (file.size / 1024).toFixed(0) } KB
                            </div>
                        `;
                        galleryPreviewContainer.appendChild(item);
                    };
                    reader.readAsDataURL(file);
                }
            });
        });
    }

    // 3. Drop Zone Handlers
    const dropZones = document.querySelectorAll('.file-drop-zone');
    dropZones.forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        if (!input) return;

        zone.addEventListener('click', () => input.click());
        
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        
        ['dragleave', 'drop'].forEach(event => {
            zone.addEventListener(event, () => zone.classList.remove('dragover'));
        });
        
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                input.dispatchEvent(new Event('change'));
            }
        });
    });
});
