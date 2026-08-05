document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss flash alerts after a few seconds so they don't linger.
    document.querySelectorAll('.flash-alert').forEach(function (alertBox) {
        setTimeout(function () {
            alertBox.style.transition = 'opacity 0.4s ease';
            alertBox.style.opacity = '0';
            setTimeout(function () { alertBox.remove(); }, 400);
        }, 5000);
    });
});