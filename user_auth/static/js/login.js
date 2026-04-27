document.addEventListener("DOMContentLoaded", () => {
    // Floating labels functionality
    const inputs = document.querySelectorAll(".input-wrapper .form-control");
    
    inputs.forEach(input => {
        // Set initial state based on value
        if (input.value) {
            input.setAttribute("data-filled", "true");
        }
        
        // On input change
        input.addEventListener("input", () => {
            if (input.value) {
                input.setAttribute("data-filled", "true");
            } else {
                input.setAttribute("data-filled", "false");
            }
        });
    });

    // Toggle password visibility
    document.querySelectorAll(".toggle-password").forEach((btn) => {
        btn.addEventListener("click", () => {
            const input = document.getElementById(btn.dataset.target);
            if (!input) return;

            const icon = btn.querySelector("i");

            if (input.type === "password") {
                input.type = "text";
                icon.classList.replace("fa-eye", "fa-eye-slash");
            } else {
                input.type = "password";
                icon.classList.replace("fa-eye-slash", "fa-eye");
            }
        });
    });

    // Form submission loading state
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", function() {
            const submitBtn = this.querySelector(".btn-login");
            if (submitBtn) {
                submitBtn.classList.add("loading");
                submitBtn.disabled = true;
            }
        });
    }

    // Add animation to features on hover
    const featureItems = document.querySelectorAll(".feature-item");
    featureItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 0.1}s`;
        item.style.opacity = "0";
        item.style.animation = `fadeIn 0.5s ease forwards`;
        item.style.animationDelay = `${0.5 + index * 0.1}s`;
    });

    // Create keyframe animation dynamically
    const style = document.createElement("style");
    style.textContent = `
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);
});
