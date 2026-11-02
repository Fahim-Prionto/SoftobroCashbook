/**
 * SoftobroCashBook Main Script
 */

document.addEventListener('DOMContentLoaded', function () {
    // Mobile sidebar toggle
    const toggleBtn = document.getElementById('sidebarToggleBtn');
    const sidebar = document.getElementById('appSidebar');

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('show');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function (e) {
            if (window.innerWidth < 992 && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }

    // Copy to clipboard helper (e.g. bKash number or TrxID)
    window.copyToClipboard = function (text, elementId) {
        navigator.clipboard.writeText(text).then(function () {
            const el = document.getElementById(elementId);
            if (el) {
                const originalText = el.innerHTML;
                el.innerHTML = '<i class="bi bi-check2-circle text-success"></i> Copied!';
                setTimeout(() => {
                    el.innerHTML = originalText;
                }, 2000);
            }
        }).catch(function (err) {
            console.error('Failed to copy: ', err);
        });
    };

    // Print button trigger
    const printButtons = document.querySelectorAll('.btn-print-trigger');
    printButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            window.print();
        });
    });
});

