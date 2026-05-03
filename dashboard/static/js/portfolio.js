/**
 * LOFT Design - Portfolio Management JS
 * Handles previews, drag & drop, image compression, and form animations
 */

document.addEventListener('DOMContentLoaded', () => {
    /**
     * Compresses an image file using Canvas
     * @param {File} file 
     * @param {number} maxWidth 
     * @param {number} maxHeight 
     * @param {number} quality (0 to 1)
     * @returns {Promise<Blob>}
     */
    const compressImage = (file, maxWidth = 1920, maxHeight = 1080, quality = 0.7) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = (event) => {
                const img = new Image();
                img.src = event.target.result;
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    let width = img.width;
                    let height = img.height;

                    if (width > height) {
                        if (width > maxWidth) {
                            height *= maxWidth / width;
                            width = maxWidth;
                        }
                    } else {
                        if (height > maxHeight) {
                            width *= maxHeight / height;
                            height = maxHeight;
                        }
                    }

                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);

                    canvas.toBlob((blob) => {
                        resolve(blob);
                    }, 'image/jpeg', quality);
                };
                img.onerror = (err) => reject(err);
            };
            reader.onerror = (err) => reject(err);
        });
    };

    /**
     * Replaces files in a FileList-like way for an input element
     * @param {HTMLInputElement} input 
     * @param {Array<File|Blob>} files 
     */
    const updateInputFiles = (input, files) => {
        const dataTransfer = new DataTransfer();
        files.forEach((file, index) => {
            // If it's a blob from compression, we convert it back to a File
            const newFile = file instanceof File ? file : new File([file], `compressed_${index}.jpg`, { type: 'image/jpeg' });
            dataTransfer.items.add(newFile);
        });
        input.files = dataTransfer.files;
    };

    // 1. Thumbnail Preview
    const thumbInput = document.querySelector('input[name="thumbnail"]');
    const thumbPreviewContainer = document.getElementById('thumbPreviewContainer');
    
    if (thumbInput) {
        thumbInput.addEventListener('change', async function() {
            const file = this.files[0];
            if (file) {
                // Compress if > 1MB
                let fileToPreview = file;
                if (file.size > 1024 * 1024) {
                    try {
                        const compressedBlob = await compressImage(file);
                        updateInputFiles(this, [compressedBlob]);
                        fileToPreview = this.files[0];
                    } catch (e) {
                        console.error('Compression failed', e);
                    }
                }

                const reader = new FileReader();
                reader.onload = function(e) {
                    thumbPreviewContainer.innerHTML = `
                        <div class="preview-item w-100 mb-0" style="aspect-ratio: 16/9;">
                            <img src="${e.target.result}" alt="Thumbnail Preview">
                            <div class="preview-info">
                                ${(fileToPreview.size / 1024).toFixed(0)} KB (Reduced from ${(file.size / 1024).toFixed(0)} KB)
                            </div>
                        </div>
                    `;
                };
                reader.readAsDataURL(fileToPreview);
            }
        });
    }

    // 2. Gallery Preview (Multi-file)
    const galleryInput = document.querySelector('input[name="gallery_images"]');
    const galleryPreviewContainer = document.getElementById('galleryPreviewContainer');
    
    if (galleryInput) {
        galleryInput.addEventListener('change', async function() {
            const originalFiles = Array.from(this.files);
            const compressedFiles = [];
            
            galleryPreviewContainer.innerHTML = '<div class="col-12 text-center p-3"><span class="spinner-border spinner-border-sm me-2"></span>Optimizing images...</div>';

            for (const file of originalFiles) {
                if (file.type.startsWith('image/')) {
                    if (file.size > 1024 * 1024) {
                        try {
                            const compressedBlob = await compressImage(file);
                            compressedFiles.push(compressedBlob);
                        } catch (e) {
                            console.error('Compression failed', e);
                            compressedFiles.push(file);
                        }
                    } else {
                        compressedFiles.push(file);
                    }
                }
            }

            updateInputFiles(this, compressedFiles);
            galleryPreviewContainer.innerHTML = '';

            Array.from(this.files).forEach((file, index) => {
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


    // 5. AJAX Deletion with SweetAlert2
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            const name = this.getAttribute('data-name');
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            // Get translations from data attrs or defaults
            const title = this.getAttribute('data-swal-title') || 'Are you sure?';
            const text = this.getAttribute('data-swal-text') || `You are about to delete "${name}".`;
            const confirmText = this.getAttribute('data-swal-confirm') || 'Yes, delete it';
            const cancelText = this.getAttribute('data-swal-cancel') || 'Cancel';

            Swal.fire({
                title: title,
                text: text,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: 'var(--brand-danger)',
                cancelButtonColor: 'var(--brand-secondary)',
                confirmButtonText: confirmText,
                cancelButtonText: cancelText,
                reverseButtons: true,
                background: '#fff',
                customClass: {
                    popup: 'rounded-4 border-0',
                    confirmButton: 'rounded-pill px-4',
                    cancelButton: 'rounded-pill px-4'
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    fetch(url, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken,
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            Swal.fire({
                                title: 'Deleted!',
                                text: data.message,
                                icon: 'success',
                                confirmButtonColor: 'var(--brand-primary)'
                            }).then(() => {
                                window.location.reload();
                            });
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                    });
                }
            });
        });
    // 6. Category Creation AJAX
    const categoryForm = document.getElementById('categoryForm');
    if (categoryForm) {
        categoryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const url = this.getAttribute('action');
            const submitBtn = this.querySelector('button[type="submit"]');
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating...';

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Swal.fire({
                        title: 'Success!',
                        text: data.message,
                        icon: 'success',
                        confirmButtonColor: 'var(--brand-primary)'
                    }).then(() => {
                        if (data.redirect_url) {
                            window.location.href = data.redirect_url;
                        } else {
                            window.location.reload();
                        }
                    });
                } else {
                    // Handled by common errorList partial if used, 
                    // but we can show a swal here too for modal context
                    Swal.fire({
                        title: 'Error',
                        text: data.errors ? data.errors[0] : 'Something went wrong',
                        icon: 'error'
                    });
                }
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Create Category';
            });
        });
    }
});
