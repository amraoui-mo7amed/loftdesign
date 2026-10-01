/**
 * LOFT Design - Contact Request Leads JS
 * Handles AJAX deletions and detail modals via SweetAlert2
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. View Lead Details Modal
    const viewDetailsButtons = document.querySelectorAll('.view-lead-details-btn');
    viewDetailsButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const name = this.getAttribute('data-name');
            const phone = this.getAttribute('data-phone');
            const projectType = this.getAttribute('data-project');
            const message = this.getAttribute('data-message');
            const date = this.getAttribute('data-date');

            Swal.fire({
                title: `<span class="fw-black text-uppercase">${name}</span>`,
                html: `
                    <div class="text-start p-2">
                        <div class="mb-3 p-3 bg-light rounded-4">
                            <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Project Preference</label>
                            <span class="badge bg-dark fs-6 rounded-pill px-3 py-2">${projectType}</span>
                        </div>
                        <div class="row g-3">
                            <div class="col-6">
                                <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Phone</label>
                                <div class="fw-bold text-dark">${phone}</div>
                            </div>
                            <div class="col-6">
                                <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Received Date</label>
                                <div class="text-muted small">${date}</div>
                            </div>
                            <div class="col-12">
                                <label class="smaller text-muted text-uppercase fw-bold d-block mb-1">Message</label>
                                <p class="text-dark bg-light p-3 rounded-4 mb-0 border-start border-4 border-primary">${message}</p>
                            </div>
                        </div>
                    </div>
                `,
                confirmButtonText: gettext('CLOSE'),
                confirmButtonColor: 'var(--brand-dark)',
                customClass: {
                    popup: 'rounded-5 border-0',
                    confirmButton: 'rounded-pill px-5 py-3 fw-bold'
                }
            });
        });
    });
});
