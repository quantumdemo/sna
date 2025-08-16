document.addEventListener('DOMContentLoaded', () => {
    // Phase 7 Carousel
    const carousel = document.querySelector('.carousel');
    if (carousel) {
        const items = carousel.querySelectorAll('.carousel-item');
        let currentIndex = 0;
        const totalItems = items.length;

        if (totalItems > 1) {
            setInterval(() => {
                currentIndex = (currentIndex + 1) % totalItems;
                carousel.style.transform = `translateX(-${currentIndex * 100}%)`;
            }, 5000); // Change slide every 5 seconds
        }
    }

    // Phase 11 Carousel
    const lifeCarousel = document.querySelector('.life-carousel');
    if (lifeCarousel) {
        const lifeItems = lifeCarousel.querySelectorAll('.life-carousel-item');
        let currentLifeIndex = 0;
        const totalLifeItems = lifeItems.length;

        if (totalLifeItems > 1) {
            // Add navigation buttons for this carousel
            const prevButton = document.createElement('button');
            prevButton.innerHTML = '&#10094;';
            prevButton.className = 'carousel-nav prev';
            lifeCarousel.appendChild(prevButton);

            const nextButton = document.createElement('button');
            nextButton.innerHTML = '&#10095;';
            nextButton.className = 'carousel-nav next';
            lifeCarousel.appendChild(nextButton);

            const updateCarousel = () => {
                lifeCarousel.style.transform = `translateX(-${currentLifeIndex * 100}%)`;
            };

            nextButton.addEventListener('click', () => {
                currentLifeIndex = (currentLifeIndex + 1) % totalLifeItems;
                updateCarousel();
            });

            prevButton.addEventListener('click', () => {
                currentLifeIndex = (currentLifeIndex - 1 + totalLifeItems) % totalLifeItems;
                updateCarousel();
            });
        }
    }
});
