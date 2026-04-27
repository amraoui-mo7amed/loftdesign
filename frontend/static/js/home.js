/**
 * LOFT Design - Landing Page JavaScript
 * Handles scroll effects and navbar transitions
 */

document.addEventListener('DOMContentLoaded', () => {
    const nav = document.getElementById('landingNav');
    const heroSection = document.querySelector('.hero-section');
    
    const handleScroll = () => {
        if (window.scrollY > 50) {
            nav.classList.add('bg-white', 'shadow-sm', 'py-2');
            nav.classList.remove('navbar-dark', 'py-4');
            nav.classList.add('navbar-light');
        } else {
            nav.classList.remove('bg-white', 'shadow-sm', 'py-2', 'navbar-light');
            nav.classList.add('navbar-dark', 'py-4');
        }
    };

    // Initial check
    handleScroll();

    // Scroll listener
    window.addEventListener('scroll', handleScroll);

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
