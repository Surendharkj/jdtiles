document.addEventListener("DOMContentLoaded", () => {
  // Hero slideshows (tiles/properties)
  const heroCards = document.querySelectorAll(".hero-card[data-images]");
  heroCards.forEach((card) => {
    let images = [];
    try {
      images = JSON.parse(card.getAttribute("data-images") || "[]");
    } catch {
      images = [];
    }

    const fallback =
      card.classList.contains("hero-tile-card")
        ? "linear-gradient(135deg, #111, #333)"
        : "linear-gradient(135deg, #202020, #050505)";

    if (!images.length) {
      card.style.backgroundImage = fallback;
      return;
    }

    let idx = 0;
    card.style.backgroundImage = `url("${images[0]}")`;

    // Preload next images for smoother transitions
    images.slice(0, 6).forEach((src) => {
      const img = new Image();
      img.src = src;
    });

    setInterval(() => {
      idx = (idx + 1) % images.length;
      card.style.backgroundImage = `url("${images[idx]}")`;
    }, 3500);
  });

  // Detail gallery: switch main media between image and video.
  document.querySelectorAll(".detail-thumbs .thumb").forEach((btn) => {
    btn.addEventListener("click", () => {
      const src = btn.getAttribute("data-main-src");
      const kind = btn.getAttribute("data-main-kind") || "image";
      const layout = btn.closest(".detail-layout");
      if (!layout || !src) return;

      const mainImage = layout.querySelector('.detail-main-image img[data-kind="image"]');
      const mainVideo = layout.querySelector('.detail-main-image video[data-kind="video"]');

      if (kind === "video") {
        if (mainVideo) {
          mainVideo.classList.remove("is-hidden");
          mainVideo.src = src;
        }
        if (mainImage) {
          mainImage.classList.add("is-hidden");
        }
      } else {
        if (mainImage) {
          mainImage.classList.remove("is-hidden");
          mainImage.src = src;
        }
        if (mainVideo) {
          mainVideo.classList.add("is-hidden");
          mainVideo.pause?.();
          mainVideo.removeAttribute("src");
          mainVideo.load?.();
        }
      }
    });
  });
});

