document.addEventListener('DOMContentLoaded', () => {
    // Hamburger menu toggle
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // Active link highlighting
    const currentLocation = window.location.pathname;
    const allLinks = document.querySelectorAll('.nav-links a');

    allLinks.forEach(link => {
        if (link.getAttribute('href') === currentLocation) {
            link.classList.add('active-link');
        }
    });
});
