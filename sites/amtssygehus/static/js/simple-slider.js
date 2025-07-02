class Slider {
    constructor(slideshowSelector, slidesSelector) {
        this.container = document.querySelector(slideshowSelector);
        this.slides = Array.from(this.container.querySelectorAll(slidesSelector));
        this.currentIndex = 0;

        this.createArrows();
        this.updateSlides();
    }

    createArrows() {
        const controls = document.createElement('div');
        controls.className = 'slider-controls';

        const leftArrow = document.createElement('div');
        leftArrow.className = 'slider-left';
        leftArrow.innerHTML = `
            <svg class="arrow-left" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#1f1f1f">
                <path d="M400-80 0-480l400-400 71 71-329 329 329 329-71 71Z"></path>
            </svg>`;
        leftArrow.addEventListener('click', () => this.showSlide(this.currentIndex - 1));

        const rightArrow = document.createElement('div');
        rightArrow.className = 'slider-right';
        rightArrow.innerHTML = `
            <svg class="arrow-right" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#1f1f1f">
                <path d="m321-80-71-71 329-329-329-329 71-71 400 400L321-80Z"></path>
            </svg>`;
        rightArrow.addEventListener('click', () => this.showSlide(this.currentIndex + 1));

        controls.appendChild(leftArrow);
        controls.appendChild(rightArrow);
        this.container.appendChild(controls);
    }

    showSlide(index) {
        this.slides[this.currentIndex].classList.remove('active');
        this.currentIndex = (index + this.slides.length) % this.slides.length;
        this.updateSlides();
    }

    updateSlides() {
        this.slides[this.currentIndex].classList.add('active');
    }
}

export { Slider };