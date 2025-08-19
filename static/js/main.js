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

    // Admin Course Form Accordion
    const courseFormPanel = document.querySelector('.course-form-panel');
    if (courseFormPanel) {
        const formToggle = courseFormPanel.querySelector('h3');
        formToggle.addEventListener('click', () => {
            courseFormPanel.classList.toggle('is-open');
        });
    }

    // Admin Chat Mobile View Toggle
    const chatContainer = document.querySelector('.admin-chat-container');
    if (chatContainer) {
        const chatListItems = chatContainer.querySelectorAll('.chat-list-item');
        const backBtn = chatContainer.querySelector('.back-to-list-btn');

        chatListItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                chatContainer.classList.add('chat-view-active');
            });
        });

        if (backBtn) {
            backBtn.addEventListener('click', () => {
                chatContainer.classList.remove('chat-view-active');
            });
        }
    }

    // More Actions Dropdown
    document.addEventListener('click', (e) => {
        const isDropdownButton = e.target.matches('.more-actions-toggle');
        if (!isDropdownButton && e.target.closest('.mobile-actions') === null) {
            document.querySelectorAll('.more-actions-dropdown').forEach(dropdown => {
                dropdown.classList.remove('is-open');
            });
        } else if (isDropdownButton) {
            const dropdown = e.target.nextElementSibling;
            dropdown.classList.toggle('is-open');
        }
    });
});
