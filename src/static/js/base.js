const csrfToken = '{{ csrf_token }}';
    // Modern Dark/Light Mode Toggle
    function setTheme(theme) {
        const html = document.documentElement;
        const icon = document.getElementById('theme-toggle-icon');
        if (theme === 'dark') {
            html.setAttribute('data-theme', 'dark');
            icon.className = 'fas fa-sun';
        } else {
            html.removeAttribute('data-theme');
            icon.className = 'fas fa-moon';
        }
        localStorage.setItem('theme', theme);
    }
    document.addEventListener('DOMContentLoaded', function() {
        const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        setTheme(savedTheme);
        document.getElementById('theme-toggle').addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            setTheme(currentTheme === 'dark' ? 'light' : 'dark');
        });
        // Initialize tooltips and popovers
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    });