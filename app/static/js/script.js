// Add any theme-specific or dynamic JavaScript here
// Example: Initialize Bootstrap tooltips if you use them
document.addEventListener('DOMContentLoaded', function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    console.log("Pandora PM Script Loaded");

    // Add more JS interactions as needed
    // e.g., confirm dialogues, AJAX calls, etc.
});