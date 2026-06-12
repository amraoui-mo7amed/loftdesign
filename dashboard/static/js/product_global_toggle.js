document.addEventListener("DOMContentLoaded", function () {
    var csrf = document.querySelector('[name=csrfmiddlewaretoken]');
    var token = csrf ? csrf.value : "";

    document.querySelectorAll(".editorial-global-toggle").forEach(function (cb) {
        cb.addEventListener("change", function () {
            var url = this.dataset.url;
            var wasChecked = !this.checked;

            fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": token,
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success) {
                    cb.checked = wasChecked;
                    if (typeof Swal !== "undefined") {
                        Swal.fire({
                            icon: "error",
                            title: gettext("Error"),
                            text: data.message || gettext("Failed to update.")
                        });
                    }
                }
            })
            .catch(function () {
                cb.checked = wasChecked;
                if (typeof Swal !== "undefined") {
                    Swal.fire({
                        icon: "error",
                        title: gettext("Error"),
                        text: gettext("Something went wrong.")
                    });
                }
            });
        });
    });
});
