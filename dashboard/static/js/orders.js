/**
 * LOFT Design - Order Management JS
 * Handles status updates via AJAX
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


});
