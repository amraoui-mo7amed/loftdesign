(function () {
  const gallery = document.getElementById("productGallery");
  const mainImg = document.getElementById("galleryMainImg");
  const thumbs = document.querySelectorAll(".gallery-thumb");
  const prevBtn = document.querySelector(".gallery-prev");
  const nextBtn = document.querySelector(".gallery-next");

  if (!gallery || !mainImg || !thumbs.length) return;

  const images = gallery.dataset.images.split(",");
  let currentIndex = 0;

  function showImage(index) {
    if (index < 0) index = images.length - 1;
    if (index >= images.length) index = 0;
    currentIndex = index;
    mainImg.style.opacity = "0";
    setTimeout(function () {
      mainImg.src = images[currentIndex];
      mainImg.style.opacity = "1";
    }, 150);
    thumbs.forEach(function (t) {
      t.classList.toggle(
        "active",
        parseInt(t.dataset.index) === currentIndex
      );
    });
  }

  thumbs.forEach(function (thumb) {
    thumb.addEventListener("click", function () {
      showImage(parseInt(this.dataset.index));
    });
  });

  if (prevBtn) {
    prevBtn.addEventListener("click", function () {
      showImage(currentIndex - 1);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      showImage(currentIndex + 1);
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft") {
      if (document.dir === "rtl") {
        showImage(currentIndex + 1);
      } else {
        showImage(currentIndex - 1);
      }
    }
    if (e.key === "ArrowRight") {
      if (document.dir === "rtl") {
        showImage(currentIndex - 1);
      } else {
        showImage(currentIndex + 1);
      }
    }
  });
})();
