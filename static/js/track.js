(function () {
    const trackPage = document.querySelector('.track-page');
    if (!trackPage) return;

    const orderId = trackPage.dataset.orderId;
    const fillEl = document.getElementById('progress-fill');
    const statusLabelEl = document.getElementById('status-label');
    const stepEls = document.querySelectorAll('.progress-step');

    function applyStatus(step, label, totalSteps) {
        // Fill the bar proportionally to how many milestones are complete.
        const percent = (step / (totalSteps - 1)) * 100;
        fillEl.style.width = percent + '%';
        statusLabelEl.textContent = label;

        stepEls.forEach(function (el) {
            const stepIndex = parseInt(el.dataset.step, 10);
            el.classList.toggle('step-active', stepIndex <= step);
        });
    }

    function pollStatus() {
        fetch(`/api/order/${orderId}/status`)
            .then(function (response) {
                if (!response.ok) throw new Error('status fetch failed');
                return response.json();
            })
            .then(function (data) {
                applyStatus(data.status_step, data.status_label, data.total_steps);
            })
            .catch(function (err) {
                console.error('Order tracking error:', err);
            });
    }

    // Poll immediately, then every 4 seconds.
    pollStatus();
    setInterval(pollStatus, 4000);
})();
