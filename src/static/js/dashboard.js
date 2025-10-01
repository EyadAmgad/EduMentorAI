function showActivityTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.activity-tab-content');
    tabContents.forEach(content => content.style.display = 'none');

    // Remove active class from all tabs
    const tabs = document.querySelectorAll('.activity-tab');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Show selected tab content
    document.getElementById(tabName + '-tab').style.display = 'block';

    // Add active class to clicked tab
    event.target.classList.add('active');
}

// Initialize first tab as active on page load
document.addEventListener('DOMContentLoaded', function() {
    const firstTab = document.querySelector('.activity-tab.active');
    if (firstTab) {
        const tabName = firstTab.onclick.toString().match(/showActivityTab\('(\w+)'\)/)[1];
        document.getElementById(tabName + '-tab').style.display = 'block';
    }
});