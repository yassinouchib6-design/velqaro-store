const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

document.body.classList.add("animations-ready");

const clampNumberInput = (input) => {
    const min = Number(input.min) || 1;
    const max = input.max ? Number(input.max) : Infinity;
    const value = Number(input.value) || min;
    input.value = Math.min(max, Math.max(min, value));
};

document.addEventListener("input", (event) => {
    if (event.target.matches('input[type="number"]')) {
        clampNumberInput(event.target);
    }
});

document.querySelectorAll(".quantity-selector").forEach((selector) => {
    const input = selector.querySelector("[data-qty-input]");
    const form = selector.matches("form") ? selector : selector.closest("form");
    const autoSubmit = selector.hasAttribute("data-quantity-form");

    selector.querySelectorAll("[data-qty-step]").forEach((button) => {
        button.addEventListener("click", () => {
            if (!input) {
                return;
            }

            const before = Number(input.value) || Number(input.min) || 1;
            const step = Number(button.dataset.qtyStep);
            input.value = before + step;
            clampNumberInput(input);

            if (autoSubmit && form && Number(input.value) !== before) {
                if (typeof form.requestSubmit === "function") {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            }
        });
    });
});

const header = document.querySelector("[data-header]");
const syncHeader = () => {
    if (header) {
        header.classList.toggle("is-scrolled", window.scrollY > 20);
    }
};

syncHeader();
window.addEventListener("scroll", syncHeader, { passive: true });

const parallaxMedia = document.querySelector("[data-parallax]");

if (parallaxMedia && !prefersReducedMotion) {
    const maxParallax = 40;
    let ticking = false;

    const applyParallax = () => {
        const offset = Math.max(-maxParallax, Math.min(maxParallax, window.scrollY * 0.25));
        parallaxMedia.style.setProperty("--parallax-y", `${offset.toFixed(1)}px`);
        ticking = false;
    };

    applyParallax();
    window.addEventListener(
        "scroll",
        () => {
            if (!ticking) {
                requestAnimationFrame(applyParallax);
                ticking = true;
            }
        },
        { passive: true }
    );
}

const menuToggle = document.querySelector("[data-menu-toggle]");
const mobileMenu = document.querySelector("[data-mobile-menu]");

const closeMobileMenu = () => {
    if (!menuToggle || !mobileMenu) {
        return;
    }
    mobileMenu.classList.remove("is-open");
    menuToggle.setAttribute("aria-expanded", "false");
    document.body.classList.remove("menu-open");
};

if (menuToggle && mobileMenu) {
    menuToggle.addEventListener("click", () => {
        const isOpen = mobileMenu.classList.toggle("is-open");
        menuToggle.setAttribute("aria-expanded", String(isOpen));
        document.body.classList.toggle("menu-open", isOpen);
    });

    mobileMenu.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", closeMobileMenu);
    });
}

const revealItems = document.querySelectorAll(".reveal");

if (prefersReducedMotion) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
} else if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.14 }
    );

    revealItems.forEach((item) => observer.observe(item));
} else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
}

document.querySelectorAll(".zoom-media").forEach((media) => {
    media.addEventListener("mousemove", (event) => {
        if (prefersReducedMotion) {
            return;
        }
        const rect = media.getBoundingClientRect();
        media.style.setProperty("--zoom-x", `${((event.clientX - rect.left) / rect.width) * 100}%`);
        media.style.setProperty("--zoom-y", `${((event.clientY - rect.top) / rect.height) * 100}%`);
    });
});

const tiltEnabled = !prefersReducedMotion && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

if (tiltEnabled) {
    document.querySelectorAll(".product-card").forEach((card) => {
        const maxTilt = 6;

        const handleTiltMove = (event) => {
            const rect = card.getBoundingClientRect();
            const relativeX = (event.clientX - rect.left) / rect.width;
            const relativeY = (event.clientY - rect.top) / rect.height;
            const tiltX = (relativeX - 0.5) * maxTilt * 2;
            const tiltY = (0.5 - relativeY) * maxTilt * 2;
            card.style.setProperty("--tilt-x", `${tiltX.toFixed(2)}deg`);
            card.style.setProperty("--tilt-y", `${tiltY.toFixed(2)}deg`);
        };

        const resetTilt = () => {
            card.style.setProperty("--tilt-x", "0deg");
            card.style.setProperty("--tilt-y", "0deg");
        };

        card.addEventListener("mousemove", handleTiltMove);
        card.addEventListener("mouseleave", resetTilt);
    });
}

document.querySelectorAll(".thumb-row img").forEach((thumb) => {
    thumb.addEventListener("click", () => {
        const gallery = thumb.closest(".product-gallery");
        const mainImage = gallery && gallery.querySelector(".detail-media img");
        if (mainImage) {
            mainImage.src = thumb.src;
            mainImage.alt = thumb.alt;
        }
    });
});

const slider = document.querySelector("[data-slider]");
const sliderPrev = document.querySelector("[data-slider-prev]");
const sliderNext = document.querySelector("[data-slider-next]");

document.querySelectorAll("[data-featured-products]").forEach((section) => {
    if (section.querySelector(".product-card")) {
        section.querySelectorAll(".loading-skeleton, [data-skeleton]").forEach((placeholder) => {
            placeholder.remove();
        });
    }
});

if (slider && sliderPrev && sliderNext) {
    const slideBy = () => Math.min(360, slider.clientWidth * 0.78);
    sliderPrev.addEventListener("click", () => slider.scrollBy({ left: -slideBy(), behavior: prefersReducedMotion ? "auto" : "smooth" }));
    sliderNext.addEventListener("click", () => slider.scrollBy({ left: slideBy(), behavior: prefersReducedMotion ? "auto" : "smooth" }));
}

document.querySelectorAll(".button").forEach((button) => {
    button.addEventListener("click", (event) => {
        if (prefersReducedMotion || button.disabled) {
            return;
        }
        const rect = button.getBoundingClientRect();
        const ripple = document.createElement("span");
        ripple.className = "ripple";
        ripple.style.left = `${event.clientX - rect.left}px`;
        ripple.style.top = `${event.clientY - rect.top}px`;
        button.appendChild(ripple);
        ripple.addEventListener("animationend", () => ripple.remove());
    });
});

document.querySelectorAll("[data-modal-close]").forEach((control) => {
    control.addEventListener("click", () => {
        const modal = control.closest("[data-modal]");
        if (modal) {
            modal.hidden = true;
        }
    });
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeMobileMenu();
        document.querySelectorAll("[data-modal]:not([hidden])").forEach((modal) => {
            modal.hidden = true;
        });
    }
});

const cartCount = document.querySelector("[data-cart-count]");
if (cartCount && Number(cartCount.textContent.trim()) > 0 && !prefersReducedMotion) {
    cartCount.classList.add("bump");
    setTimeout(() => cartCount.classList.remove("bump"), 400);
}
