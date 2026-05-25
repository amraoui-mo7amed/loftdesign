/**
 * LOFT Design - Order Management JS
 * Handles status updates and detail modal via SweetAlert2
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Status Update AJAX
    const statusButtons = document.querySelectorAll('.update-status-btn');
    statusButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('data-url');
            const status = this.getAttribute('data-status');
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            fetch(url, {
                method: 'POST',
                body: new URLSearchParams({ 'status': status }),
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });

    // 2. View Details via SweetAlert2 (Using data attributes)
    const detailButtons = document.querySelectorAll('.view-details-btn');
    detailButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const isLimited = this.getAttribute('data-limited') === 'true';
            const product = this.getAttribute('data-product');
            const date = this.getAttribute('data-date');

            if (isLimited) {
                Swal.fire({
                    title: `<span class="fw-black text-uppercase">${product}</span>`,
                    html: `
                        <div class="text-start p-2">
                            <div class="mb-3 p-3 bg-light rounded-4">
                                <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Product</label>
                                <div class="fw-black text-dark">${product}</div>
                            </div>
                            <div class="row g-3">
                                <div class="col-12">
                                    <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Order Date</label>
                                    <div class="text-muted small">${date}</div>
                                </div>
                            </div>
                        </div>
                    `,
                    confirmButtonText: 'CLOSE',
                    confirmButtonColor: 'var(--brand-dark)',
                    customClass: {
                        popup: 'rounded-5 border-0',
                        confirmButton: 'rounded-pill px-5 py-3 fw-bold'
                    }
                });
            } else {
                const name = this.getAttribute('data-name');
                const phone = this.getAttribute('data-phone');
                const location = this.getAttribute('data-location');
                const address = this.getAttribute('data-address') || 'N/A';

                Swal.fire({
                    title: `<span class="fw-black text-uppercase">${name}</span>`,
                    html: `
                        <div class="text-start p-2">
                            <div class="mb-3 p-3 bg-light rounded-4">
                                <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Product Inquired</label>
                                <div class="fw-black text-dark">${product}</div>
                            </div>
                            <div class="row g-3">
                                <div class="col-6">
                                    <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Phone</label>
                                    <div class="fw-bold text-dark">${phone}</div>
                                </div>
                                <div class="col-6">
                                    <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Location</label>
                                    <div class="fw-bold text-dark">${location}</div>
                                </div>
                                <div class="col-12">
                                    <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Specific Address</label>
                                    <div class="text-muted small">${address}</div>
                                </div>
                                <div class="col-12">
                                    <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Inquiry Date</label>
                                    <div class="text-muted small">${date}</div>
                                </div>
                            </div>
                        </div>
                    `,
                    confirmButtonText: 'CLOSE',
                    confirmButtonColor: 'var(--brand-dark)',
                    customClass: {
                        popup: 'rounded-5 border-0',
                        confirmButton: 'rounded-pill px-5 py-3 fw-bold'
                    }
                });
            }
        });
    });
});
