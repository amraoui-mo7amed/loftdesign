/* Products List JavaScript */
document.addEventListener("DOMContentLoaded", () => {
    // 1. Image Reveal Animation
    const mainImg = document.querySelector('.img-reveal');
    if (mainImg) {
        setTimeout(() => {
            mainImg.classList.add('active');
        }, 100);
    }

    // 2. Floating Button Entry
    const floatBtn = document.querySelector('.floating-visualize-btn');
    if (floatBtn) {
        setTimeout(() => {
            floatBtn.classList.add('active');
        }, 800);
    }

    // 3. Scroll Reveal Logic
    const revealElements = document.querySelectorAll('.scroll-reveal');
    const revealOnScroll = () => {
        revealElements.forEach(el => {
            const rect = el.getBoundingClientRect();
            const viewHeight = window.innerHeight || document.documentElement.clientHeight;
            if (rect.top <= viewHeight * 0.9) {
                el.classList.add('active');
            }
        });
    };

    window.addEventListener('scroll', revealOnScroll);
    revealOnScroll(); // Trigger once on load

    console.log("Product detail interactions initialized.");
});
