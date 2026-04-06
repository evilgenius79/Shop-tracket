/**
 * LotTracker - Custom JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {

    // Auto-uppercase VIN fields
    document.querySelectorAll('input[placeholder*="VIN"], input.font-monospace').forEach(function (el) {
        el.addEventListener('input', function () {
            const pos = this.selectionStart;
            this.value = this.value.toUpperCase();
            this.setSelectionRange(pos, pos);
        });
    });

    // Confirm dangerous actions
    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function () {
        document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(function (el) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
            if (bsAlert) bsAlert.close();
        });
    }, 5000);

    // Tooltips
    document.querySelectorAll('[title]').forEach(function (el) {
        new bootstrap.Tooltip(el, { trigger: 'hover' });
    });

    // Highlight current table row on hover (already done via CSS but extra feedback)
    document.querySelectorAll('.table tbody tr').forEach(function (row) {
        row.style.cursor = 'default';
    });

    // Make entire table rows clickable if they have a primary link
    document.querySelectorAll('.table-row-clickable').forEach(function (row) {
        const link = row.querySelector('a');
        if (link) {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function (e) {
                if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' ||
                    e.target.closest('form') || e.target.closest('.dropdown')) return;
                window.location.href = link.href;
            });
        }
    });

});
