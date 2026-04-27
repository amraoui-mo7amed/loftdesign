document.addEventListener("DOMContentLoaded", () => {
    // Utility for AJAX requests with SweetAlert2
    const handleAction = (btnId, formId, icon) => {
        const btn = document.getElementById(btnId);
        if (!btn) return;

        btn.addEventListener("click", () => {
            const config = {
                title: btn.dataset.swalTitle || 'Are you sure?',
                text: btn.dataset.swalText || '',
                icon: icon,
                showCancelButton: true,
                confirmButtonText: btn.dataset.swalConfirm || 'Confirm',
                cancelButtonText: btn.dataset.swalCancel || 'Cancel',
                showLoaderOnConfirm: true,
                reverseButtons: true,
                preConfirm: async () => {
                    const form = document.getElementById(formId);
                    if (!form) {
                        Swal.showValidationMessage('Form not found');
                        return false;
                    }

                    const formData = new FormData(form);
                    try {
                        const response = await fetch(form.action, {
                            method: 'POST',
                            body: formData,
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value
                            }
                        });

                        const data = await response.json();
                        if (!response.ok || !data.success) {
                            throw new Error(data.message || response.statusText);
                        }
                        return data;
                    } catch (error) {
                        Swal.showValidationMessage(`${error.message}`);
                    }
                },
                allowOutsideClick: () => !Swal.isLoading()
            };

            // Custom colors based on action type
            if (icon === 'warning') {
                config.confirmButtonColor = '#d33';
            } else if (icon === 'question') {
                config.confirmButtonColor = '#28a745';
            }

            Swal.fire(config).then((result) => {
                if (result.isConfirmed && result.value) {
                    Swal.fire({
                        title: btn.dataset.swalSuccessTitle || 'Success!',
                        text: result.value.message,
                        icon: 'success'
                    }).then(() => {
                        if (result.value.redirect_url) {
                            window.location.href = result.value.redirect_url;
                        } else {
                            window.location.reload();
                        }
                    });
                }
            });
        });
    };

    // Initialize actions
    handleAction("deleteUserBtn", "deleteUserForm", "warning");
    handleAction("approveUserBtn", "approveUserForm", "question");
});
