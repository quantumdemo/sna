document.addEventListener('DOMContentLoaded', () => {
    const mobileFilterButton = document.querySelector('.mobile-filter-toggle');
    const filterPanelWrapper = document.querySelector('.filters-panel-wrapper');

    if (mobileFilterButton && filterPanelWrapper) {
        mobileFilterButton.addEventListener('click', () => {
            filterPanelWrapper.classList.toggle('is-open');
        });

        // Close the panel when clicking on the background overlay
        filterPanelWrapper.addEventListener('click', (event) => {
            if (event.target === filterPanelWrapper) {
                filterPanelWrapper.classList.remove('is-open');
            }
        });
    }
});
