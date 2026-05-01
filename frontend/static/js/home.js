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
            nav.classList.remove('navbar-dark', 'py-4');
            nav.classList.add('navbar-light');
        } else {
            nav.classList.remove( 'shadow-sm', 'py-2', 'navbar-light');
            nav.classList.add('navbar-dark', 'py-4');
        }
    };

    // Initial check
    handleScroll();

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
});
