const header = document.querySelector("[data-header]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const mobileMenu = document.querySelector("[data-mobile-menu]");
const bookingForm = document.querySelector("[data-booking-form]");
const formNote = document.querySelector("[data-form-note]");
const lightbox = document.querySelector("[data-lightbox]");
const lightboxImage = document.querySelector("[data-lightbox-image]");
const lightboxClose = document.querySelector("[data-lightbox-close]");

const galleryImages = [
  {
    src: "./assets/enhanced/gallery-dining-table.jpg",
    alt: "Сервированный стол у больших окон",
  },
  {
    src: "./assets/enhanced/gallery-cocktail.jpg",
    alt: "Зелёный коктейль с цитрусом",
  },
  {
    src: "./assets/enhanced/gallery-greenhouse-interior.jpg",
    alt: "Вечерний интерьер ресторана с зеленью",
  },
  {
    src: "./assets/enhanced/gallery-plated-dish.jpg",
    alt: "Блюдо с зеленью и грибами",
  },
  {
    src: "./assets/enhanced/gallery-lounge.jpg",
    alt: "Уютный лаунж-уголок с растениями",
  },
];

function updateHeader() {
  header?.classList.toggle("is-scrolled", window.scrollY > 18);
}

function closeMenu() {
  document.body.classList.remove("menu-open");
  header?.classList.remove("is-open");
  mobileMenu?.classList.remove("is-open");
  menuToggle?.setAttribute("aria-expanded", "false");
}

function toggleMenu() {
  const nextState = menuToggle?.getAttribute("aria-expanded") !== "true";
  document.body.classList.toggle("menu-open", nextState);
  header?.classList.toggle("is-open", nextState);
  mobileMenu?.classList.toggle("is-open", nextState);
  menuToggle?.setAttribute("aria-expanded", String(nextState));
}

window.addEventListener("scroll", updateHeader, { passive: true });
updateHeader();

menuToggle?.addEventListener("click", toggleMenu);

mobileMenu?.addEventListener("click", (event) => {
  if (event.target instanceof HTMLAnchorElement) {
    closeMenu();
  }
});

document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", (event) => {
    const id = anchor.getAttribute("href");
    if (!id || id === "#") return;

    const target = document.querySelector(id);
    if (!target) return;

    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

bookingForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(bookingForm);
  const date = formData.get("date");
  const time = formData.get("time");
  const guests = formData.get("guests");

  if (formNote) {
    formNote.textContent = `Подобрали варианты на ${date}, ${time}, ${guests}. Администратор свяжется с вами для подтверждения.`;
  }
});

document.querySelectorAll("[data-gallery]").forEach((button) => {
  button.addEventListener("click", () => {
    const image = galleryImages[Number(button.dataset.gallery)];
    if (!image || !lightbox || !lightboxImage) return;

    lightboxImage.src = image.src;
    lightboxImage.alt = image.alt;

    if (typeof lightbox.showModal === "function") {
      lightbox.showModal();
    }
  });
});

lightboxClose?.addEventListener("click", () => {
  lightbox?.close();
});

lightbox?.addEventListener("click", (event) => {
  if (event.target === lightbox) {
    lightbox.close();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeMenu();
  }
});

window.addEventListener("load", () => {
  window.lucide?.createIcons();
});
