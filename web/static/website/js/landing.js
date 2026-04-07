const races = [
  { name: "Human", role: "Ranger", img: "" },
  { name: "Elf", role: "Moon Mage", img: "" },
  { name: "Dwarf", role: "Warrior", img: "" },
  { name: "Halfling", role: "Thief", img: "" },
];

const heroImageFiles = [
  "hero.png",
  "ChatGPT Image Apr 6, 2026, 08_20_55 PM.png",
  "Autumn warriors by the lake (1).png",
  "ChatGPT Image Apr 6, 2026, 03_59_34 PM.png",
  "Warrior mage and runesmith in forge.png",
  "Healing through music and magic.png",
  "ChatGPT Image Apr 6, 2026, 06_28_08 PM.png",
  "ChatGPT Image Apr 6, 2026, 07_07_15 PM.png",
  "Elothien defenders in a haunted graveyard.png",
  "Elven guardians of the spring city.png",
  "Moonlit guardians of the hamlet.png",
  "Nightwatch atop the city rooftops.png",
  "Ranger in twilight forest aiming at stag.png",
  "The rogue's secret heist.png",
  "Twilight market antics.png",
  "Warrior amidst fiery chaos.png",
  "Warriors of the fiery forge.png",
];

function heroImageUrl(fileName) {
  return `/static/website/images/${encodeURIComponent(fileName)}`;
}

function heroImageLabel(fileName) {
  return fileName
    .replace(/\.[^.]+$/, "")
    .replace(/ChatGPT Image Apr 6, 2026, /g, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function buildHeroSlides(track) {
  track.innerHTML = "";

  heroImageFiles.forEach((fileName, index) => {
    const slide = document.createElement("figure");
    slide.className = index === 0 ? "hero-slide is-active" : "hero-slide";
    slide.dataset.heroSlide = "";
    slide.setAttribute("role", "img");
    slide.setAttribute("aria-label", heroImageLabel(fileName));
    slide.style.backgroundImage = `url("${heroImageUrl(fileName)}")`;
    slide.setAttribute("aria-hidden", index === 0 ? "false" : "true");
    track.appendChild(slide);
  });
}

function buildHeroDots(slides, dotsHost, onSelect) {
  dotsHost.innerHTML = "";
  slides.forEach((_, index) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = "hero-slider-dot";
    dot.setAttribute("aria-label", `Show hero image ${index + 1}`);
    dot.addEventListener("click", () => onSelect(index));
    dotsHost.appendChild(dot);
  });
}

function initHeroSlider(root) {
  const track = root.querySelector("[data-hero-track]");
  const prev = root.querySelector("[data-hero-prev]");
  const next = root.querySelector("[data-hero-next]");
  const dotsHost = root.querySelector("[data-hero-dots]");
  const autoplayDelay = 5000;

  if (!track || !prev || !next || !dotsHost) {
    return;
  }

  buildHeroSlides(track);

  const slides = Array.from(root.querySelectorAll("[data-hero-slide]"));

  if (!slides.length) {
    return;
  }

  let currentIndex = 0;
  let autoplayId = null;

  const sync = () => {
    const dots = Array.from(dotsHost.querySelectorAll(".hero-slider-dot"));

    slides.forEach((slide, index) => {
      slide.classList.toggle("is-active", index === currentIndex);
      slide.setAttribute("aria-hidden", index === currentIndex ? "false" : "true");
    });

    dots.forEach((dot, index) => {
      dot.classList.toggle("is-active", index === currentIndex);
      dot.setAttribute("aria-pressed", index === currentIndex ? "true" : "false");
    });

    const isSingleSlide = slides.length === 1;
    prev.disabled = isSingleSlide;
    next.disabled = isSingleSlide;
  };

  const stopAutoplay = () => {
    if (autoplayId !== null) {
      window.clearInterval(autoplayId);
      autoplayId = null;
    }
  };

  const startAutoplay = () => {
    stopAutoplay();

    if (slides.length <= 1) {
      return;
    }

    autoplayId = window.setInterval(() => {
      showSlide(currentIndex + 1, { resetAutoplay: false });
    }, autoplayDelay);
  };

  const showSlide = (index, options = {}) => {
    currentIndex = (index + slides.length) % slides.length;
    sync();

    if (options.resetAutoplay !== false) {
      startAutoplay();
    }
  };

  buildHeroDots(slides, dotsHost, showSlide);

  prev.addEventListener("click", () => showSlide(currentIndex - 1));
  next.addEventListener("click", () => showSlide(currentIndex + 1));

  root.addEventListener("mouseenter", stopAutoplay);
  root.addEventListener("mouseleave", startAutoplay);

  sync();
  startAutoplay();
}

function initLegacyHeroSlider(root) {
  const media = root.querySelector(".hero-media");
  const autoplayDelay = 5000;
  const fadeDuration = 900;

  if (!media || heroImageFiles.length <= 1) {
    return;
  }

  const buffer = document.createElement("div");
  buffer.className = "hero-media hero-media-buffer is-hidden";
  buffer.setAttribute("aria-hidden", "true");
  root.insertBefore(buffer, media.nextSibling);

  media.classList.remove("is-hidden");
  media.style.backgroundImage = `url("${heroImageUrl(heroImageFiles[0])}")`;
  media.setAttribute("aria-label", heroImageLabel(heroImageFiles[0]));

  let currentIndex = 0;
  let activeLayer = media;
  let inactiveLayer = buffer;

  const showSlide = (index) => {
    currentIndex = (index + heroImageFiles.length) % heroImageFiles.length;
    inactiveLayer.style.backgroundImage = `url("${heroImageUrl(heroImageFiles[currentIndex])}")`;
    inactiveLayer.setAttribute("aria-label", heroImageLabel(heroImageFiles[currentIndex]));
    inactiveLayer.classList.remove("is-hidden");
    activeLayer.classList.add("is-hidden");

    window.setTimeout(() => {
      const previousLayer = activeLayer;
      activeLayer = inactiveLayer;
      inactiveLayer = previousLayer;
    }, fadeDuration);
  };

  window.setInterval(() => {
    showSlide(currentIndex + 1);
  }, autoplayDelay);
}

function buildRaceSlides(track) {
  races.forEach((race) => {
    const slide = document.createElement("article");
    slide.className = "race-slide";

    const media = document.createElement("div");
    media.className = "race-slide-media";

    if (race.img) {
      const image = document.createElement("img");
      image.src = race.img;
      image.alt = `${race.name} concept art`;
      image.loading = "lazy";
      media.appendChild(image);
    } else {
      media.classList.add("race-slide-media-placeholder");
    }

    const overlay = document.createElement("div");
    overlay.className = "race-slide-overlay";

    const copy = document.createElement("div");
    copy.className = "race-slide-copy";
    copy.innerHTML = `<h3>${race.name}</h3><p>${race.role}</p>`;

    slide.appendChild(media);
    slide.appendChild(overlay);
    slide.appendChild(copy);
    track.appendChild(slide);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const heroSlider = document.querySelector("[data-hero-slider]");
  const legacyHeroFeed = !heroSlider ? document.querySelector(".hero-feed") : null;
  const track = document.querySelector("[data-race-track]");

  if (heroSlider) {
    initHeroSlider(heroSlider);
  } else if (legacyHeroFeed) {
    initLegacyHeroSlider(legacyHeroFeed);
  }

  if (!track) {
    return;
  }

  buildRaceSlides(track);
});