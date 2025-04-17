// pandora_pm/app/static/js/script.js
console.log("Pandora PM Script Loaded");

// Add any general frontend JavaScript here.
// Example: Confirmation for delete buttons

document.addEventListener('DOMContentLoaded', function() {
    const deleteForms = document.querySelectorAll('form.delete-confirm');

    deleteForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const message = this.dataset.confirmMessage || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                event.preventDefault(); // Stop form submission if user cancels
            }
        });
    });

    // Auto-dismiss flash messages after a delay
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            // Use Bootstrap's alert dismiss method if available
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                 const alertInstance = bootstrap.Alert.getInstance(alert);
                 if (alertInstance) {
                     alertInstance.close();
                 } else {
                     // Fallback if bootstrap JS isn't loaded or initialized properly
                     alert.style.display = 'none';
                 }
            } else {
                alert.style.display = 'none'; // Simple fallback
            }
        }, 5000); // Dismiss after 5 seconds (5000ms)
    });

});