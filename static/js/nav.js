document.addEventListener('DOMContentLoaded', () => {
  const navToggle = document.querySelector('.nav-toggle');
  const mainNav = document.querySelector('.main-nav');
  const body = document.body;

  if (navToggle && mainNav) {
    navToggle.addEventListener('click', () => {
      const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';

      mainNav.classList.toggle('is-open');
      body.classList.toggle('nav-open'); // Toggle class on body
      navToggle.setAttribute('aria-expanded', !isExpanded);
    });
  }
});
