document.addEventListener('DOMContentLoaded', () => {
  const navToggle = document.querySelector('.nav-toggle');
  const mainNav = document.querySelector('.main-nav');
  const backdrop = document.querySelector('.nav-backdrop');
  const body = document.body;

  function closeNav() {
    mainNav.classList.remove('is-open');
    backdrop.classList.remove('is-visible');
    body.classList.remove('nav-open');
    navToggle.setAttribute('aria-expanded', 'false');
  }

  function openNav() {
    mainNav.classList.add('is-open');
    backdrop.classList.add('is-visible');
    body.classList.add('nav-open');
    navToggle.setAttribute('aria-expanded', 'true');
  }

  if (navToggle && mainNav && backdrop) {
    navToggle.addEventListener('click', () => {
      const isOpen = mainNav.classList.contains('is-open');
      if (isOpen) {
        closeNav();
      } else {
        openNav();
      }
    });

    backdrop.addEventListener('click', () => {
      closeNav();
    });
  }
});
