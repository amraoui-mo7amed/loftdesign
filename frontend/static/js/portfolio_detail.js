document.addEventListener("DOMContentLoaded", () => {
    const mainImg = document.getElementById("viewerMainImg");
    if (!mainImg) return;

    const thumbs = document.querySelectorAll(".thumb-item");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");

    let currentIndex = 0;
    const images = Array.from(thumbs).map((t) => t.dataset.full);

    function updateViewer(index) {
        currentIndex = index;
        mainImg.style.opacity = "0";
        setTimeout(() => {
            mainImg.src = images[currentIndex];
            mainImg.style.opacity = "1";
        }, 300);

        thumbs.forEach((t, i) => {
            if (i === currentIndex) t.classList.add("active");
            else t.classList.remove("active");
        });

        thumbs[currentIndex].scrollIntoView({
            behavior: "smooth",
            block: "nearest",
            inline: "center",
        });
    }

    thumbs.forEach((thumb, index) => {
        thumb.addEventListener("click", () => updateViewer(index));
    });

    if (prevBtn) {
        prevBtn.addEventListener("click", () => {
            let index = currentIndex - 1;
            if (index < 0) index = images.length - 1;
            updateViewer(index);
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener("click", () => {
            let index = currentIndex + 1;
            if (index >= images.length) index = 0;
            updateViewer(index);
        });
    }
});
