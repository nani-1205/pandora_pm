// app/static/js/script.js
console.log("Avatar PM Script Loaded");

// Example: Add confirmation for admin toggle
document.addEventListener('DOMContentLoaded', () => {
    const toggleForms = document.querySelectorAll('form[action*="toggle_admin"]');
    toggleForms.forEach(form => {
        form.addEventListener('submit', (event) => {
            const button = form.querySelector('button[type="submit"]');
            const action = button.textContent.trim().toLowerCase();
            if (!confirm(`Are you sure you want to ${action} for this user?`)) {
                event.preventDefault(); // Stop form submission
            }
        });
    });
});