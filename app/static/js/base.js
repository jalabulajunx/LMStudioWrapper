// app/static/js/base.js
$(document).ready(function() {
    // Initialize theme based on localStorage
    function initializeTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        setTheme(savedTheme === 'dark');
    }

    // Set theme across the application
    function setTheme(isDark) {
        document.documentElement.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        
        // Update any theme toggles
        $('.theme-toggle-checkbox').prop('checked', isDark);
        
        // Update theme toggle buttons
        $('.theme-toggle-btn').html(
            isDark ? 
            '<i class="bi bi-sun"></i> Light Mode' : 
            '<i class="bi bi-moon"></i> Dark Mode'
        );
        
        // Update modal backgrounds
        $('.modal-content').attr('data-bs-theme', isDark ? 'dark' : 'light');
    }

    // Initialize theme
    initializeTheme();

    // Export functions for other scripts
    window.themeUtils = {
        setTheme: setTheme,
        initializeTheme: initializeTheme
    };
});