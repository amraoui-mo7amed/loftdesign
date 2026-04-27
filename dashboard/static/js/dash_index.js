document.addEventListener("DOMContentLoaded", () => {
    // Sidebar Toggle for Mobile
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggleBtn');

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('show');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth < 576 && sidebar.classList.contains('show') && !sidebar.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }

    // Active Navigation Handling
    function setActiveNavLink() {
        const links = document.querySelectorAll(".sidebar .nav-link");
        const currentUrl = window.location.pathname;

        links.forEach(link => {
            link.classList.remove("active");
            if (link.getAttribute("href") === currentUrl) {
                link.classList.add("active");
            }
        });
    }
    setActiveNavLink();

    // Generic Delete with SweetAlert2
    document.querySelectorAll(".delete_button").forEach(button => {
        button.addEventListener("click", () => {
            const deleteUrl = button.dataset.deleteUrl;
            const csrfToken = button.dataset.csrfToken;
            const itemTitle = button.dataset.itemTitle || "this item";

            Swal.fire({
                title: "Are you sure?",
                text: `You are about to delete ${itemTitle}. This action cannot be undone!`,
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: "Yes, delete it",
                cancelButtonText: "Cancel",
                buttonsStyling: false,
                customClass: {
                    confirmButton: "btn btn-danger mx-2",
                    cancelButton: "btn btn-secondary"
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    fetch(deleteUrl, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": csrfToken,
                            "X-Requested-With": "XMLHttpRequest",
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({})
                    })
                    .then(response => response.json())
                    .then(data => {
                        Swal.fire({
                            title: data.success ? "Deleted!" : "Error",
                            text: data.message || "Operation completed",
                            icon: data.success ? "success" : "error"
                        }).then(() => {
                            if (data.success) location.reload();
                        });
                    })
                    .catch(() => {
                        Swal.fire({
                            title: "Error",
                            text: "Connection failed",
                            icon: "error"
                        });
                    });
                }
            });
        });
    });
});

// Table Filtering Global Helper
function filterTable(tableId, query) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');
    const filter = query.toLowerCase();

    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        let matchFound = false;

        cells.forEach(cell => {
            const cellText = cell.innerText.toLowerCase();
            if (cellText.includes(filter)) {
                matchFound = true;
            }
        });

        row.style.display = matchFound || filter === '' ? '' : 'none';
    });
}
