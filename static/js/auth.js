document.addEventListener('DOMContentLoaded', () => {
    const toggleIcon = document.querySelector('.password-toggle-icon');

    if (toggleIcon) {
        toggleIcon.addEventListener('click', function() {
            const passwordInput = this.previousElementSibling;
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);

            // Toggle the icon
            this.classList.toggle('fa-eye');
            this.classList.toggle('fa-eye-slash');
        });
    }
});
