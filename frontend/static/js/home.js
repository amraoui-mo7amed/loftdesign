/**
 * LOFT Design - Landing Page JavaScript
 * Handles scroll effects and navbar transitions
 */

document.addEventListener('DOMContentLoaded', () => {
    const nav = document.getElementById('landingNav');
    const heroSection = document.querySelector('.hero-section');
    
    const handleScroll = () => {
        if (window.scrollY > 50) {
            nav.classList.add('shadow-sm', 'py-2');
            nav.classList.remove('py-4');
            // nav.classList.add('navbar-light');
        } else {
            nav.classList.remove( 'shadow-sm', 'py-2', 'navbar-light');
        }
    };

    // Initial check
    handleScroll();

    // Intersection Observer for scroll animations
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                // Optional: unobserve if you only want it to animate once
                // revealObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

    // Scroll listener
    window.addEventListener('scroll', handleScroll);

    // Hero Slider
    const slides = document.querySelectorAll('.hero-slide');
    if (slides.length > 1) {
        let currentSlide = 0;
        const slideInterval = 5000;

        const updateSlides = () => {
            slides.forEach((slide, index) => {
                slide.classList.remove('active', 'prev', 'next');
                if (index === currentSlide) {
                    slide.classList.add('active');
                } else if (index === (currentSlide - 1 + slides.length) % slides.length) {
                    slide.classList.add('prev');
                } else {
                    slide.classList.add('next');
                }
            });
        };

        const nextSlide = () => {
            currentSlide = (currentSlide + 1) % slides.length;
            updateSlides();
        };

        // Initialize positions
        updateSlides();
        setInterval(nextSlide, slideInterval);
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Password Toggle
    document.querySelectorAll(".password-toggle").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var input = this.parentElement.querySelector("input");
            var icon = this.querySelector("i");
            if (input.type === "password") {
                input.type = "text";
                icon.classList.remove("fa-eye");
                icon.classList.add("fa-eye-slash");
            } else {
                input.type = "password";
                icon.classList.remove("fa-eye-slash");
                icon.classList.add("fa-eye");
            }
        });
    });

});

// Contact : envoie le message du formulaire sur WhatsApp
document.getElementById('contactWhatsapp')?.addEventListener('click', (e) => {
    const form = document.getElementById('contactForm');
    if (!form) return;
    const val = (n) => (form.elements[n]?.value || '').trim();
    const type = form.querySelector('input[name="project_type"]:checked');
    const typeLabel = type ? type.nextElementSibling.textContent.trim() : '';
    const lines = [val('name'), val('phone'), typeLabel, val('message')].filter(Boolean);
    const url = `https://wa.me/${e.currentTarget.dataset.wa}?text=${encodeURIComponent(lines.join('\n'))}`;
    window.open(url, '_blank', 'noopener');
});
