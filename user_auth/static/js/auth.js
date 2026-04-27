/**
 * SOC Authentication Pages JavaScript
 * Handles password toggle and error display
 */

document.addEventListener("DOMContentLoaded", function() {
    "use strict";

    /**
     * Toggle password visibility
     * @param {string} fieldId - The ID of the password input field
     */
    function togglePassword(fieldId) {
        const input = document.getElementById(fieldId);
        const button = event.currentTarget;
        const icon = button.querySelector("i");

        if (!input || !icon) {
            return;
        }

        if (input.type === "password") {
            input.type = "text";
            icon.classList.remove("fa-eye");
            icon.classList.add("fa-eye-slash");
        } else {
            input.type = "password";
            icon.classList.remove("fa-eye-slash");
            icon.classList.add("fa-eye");
        }
    }

    // Make togglePassword globally available
    window.togglePassword = togglePassword;

    // Phone number validation - allow only numbers
    const phoneInput = document.getElementById("phone_number");
    if (phoneInput) {
        phoneInput.addEventListener("input", function() {
            // Remove any non-numeric characters
            this.value = this.value.replace(/[^0-9]/g, "");
        });
    }
});
