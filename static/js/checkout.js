document.addEventListener('DOMContentLoaded', () => {
    const datePicker = document.getElementById('date-picker');
    const timeSelect = document.getElementById('time-select');
    const confirmDate = document.getElementById('confirm-date');
    const confirmTime = document.getElementById('confirm-time');

    // Parse the slots data embedded in HTML
    const slotsData = JSON.parse(document.getElementById('slots-data').textContent);

    // Extract unique dates available in slots
    const availableDates = [...new Set(slotsData.map(s => s.date))].sort();

    if (availableDates.length > 0) {
        // Set minimum and maximum date allowed in the calendar picker
        datePicker.min = availableDates[0];
        datePicker.max = availableDates[availableDates.length - 1];
    }

    // Handle Calendar Date Change
    datePicker.addEventListener('change', () => {
        const selectedDate = datePicker.value; // YYYY-MM-DD

        // Reset Time Select
        timeSelect.innerHTML = '<option value="" disabled selected>Select Time</option>';
        timeSelect.disabled = true;
        confirmTime.textContent = '—';

        // Find matching slots for selected date
        const matchingSlots = slotsData.filter(s => s.date === selectedDate);

        if (matchingSlots.length === 0) {
            confirmDate.textContent = 'No slots on this date';
            return;
        }

        // Format Date for Confirmation Side (e.g. "Friday, May 15")
        confirmDate.textContent = matchingSlots[0].formatted_date;

        // Populate Time Dropdown
        matchingSlots.forEach(slot => {
            const option = document.createElement('option');
            option.value = slot.id;
            option.textContent = slot.full ? `${slot.label} (FULL)` : slot.label;
            option.dataset.label = slot.label;

            if (slot.full) {
                option.disabled = true;
            }

            timeSelect.appendChild(option);
        });

        // Enable Time Dropdown
        timeSelect.disabled = false;
    });

    // Handle Time Selection Change
    timeSelect.addEventListener('change', () => {
        const selectedOption = timeSelect.options[timeSelect.selectedIndex];
        if (selectedOption && selectedOption.dataset.label) {
            confirmTime.textContent = selectedOption.dataset.label;
        }
    });
});