/**
 * LOFT Design - Order Management JS
 */

document.addEventListener('DOMContentLoaded', () => {
    const updateStatusButtons = document.querySelectorAll('.update-status-btn');
    
    updateStatusButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const url = this.dataset.url;
            const status = this.dataset.status;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: `status=${status}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Swal.fire({
                        title: 'Success!',
                        text: data.message,
                        icon: 'success',
                        timer: 1500,
                        showConfirmButton: false,
                        background: '#fff',
                        customClass: {
                            popup: 'rounded-4 border-0 shadow'
                        }
                    }).then(() => location.reload());
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });
});
