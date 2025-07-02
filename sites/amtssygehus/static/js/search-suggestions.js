
const imageContainer = document.querySelector(".horizontal-slider .image-container");
const images = Array.from(document.querySelectorAll(".horizontal-slider .image-item"));
let sliderId = '';

function getVisibleImageIndexes() {
    let containerRect = imageContainer.getBoundingClientRect();
    let visibleIndexes = [];

    images.forEach((img, index) => {
        let imgRect = img.getBoundingClientRect();
        let visibleWidth = Math.min(imgRect.right, containerRect.right) - Math.max(imgRect.left, containerRect.left);
        let visibilityRatio = visibleWidth / imgRect.width;

        if (visibilityRatio >= 1) {
            visibleIndexes.push(index);
        }
    });

    return visibleIndexes;
}

function scrollByImage(direction) {
    const visible = getVisibleImageIndexes();
    let targetIndex =
        direction === "left"
            ? (visible[0] - 1 + images.length) % images.length
            : (visible[visible.length - 1] + 1) % images.length;

    const target = images[targetIndex];
    const left = target.offsetLeft - imageContainer.offsetLeft;
    imageContainer.scrollTo({ left, behavior: "auto" });

    sessionStorage.setItem(sliderId, left);
}

const arrowLeft = document.querySelector(".horizontal-slider .arrow-left-container");
const arrowRight = document.querySelector(".horizontal-slider .arrow-right-container");

function disabledArrows() {

    // wait for the scroll to finish
    setTimeout(() => {
        if (getVisibleImageIndexes().includes(0)) {
            arrowLeft.classList.add("disabled");
        } else {
            arrowLeft.classList.remove("disabled");
        }

        if (getVisibleImageIndexes().includes(images.length - 1)) {
            arrowRight.classList.add("disabled");
        } else {
            arrowRight.classList.remove("disabled");
        }
    }, 10);
}

arrowLeft.addEventListener("click", () => {

    // Check if the left arrow is disabled
    if (arrowLeft.classList.contains("disabled")) {
        return
    }

    scrollByImage("left");
    disabledArrows();
});

arrowRight.addEventListener("click", (event) => {

    // Check if the right arrow is disabled
    if (arrowRight.classList.contains("disabled")) {
        return
    }

    scrollByImage("right");
    disabledArrows();
});


let scrollTimeout;
imageContainer.addEventListener("scroll", () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
        disabledArrows();
    }, 50);
});

function initializeSlider(id) {
    sliderId = `left-${id}`;
    if (sessionStorage.getItem(sliderId)) {
        imageContainer.scrollTo({
            left: sessionStorage.getItem(sliderId),
            behavior: 'auto'
        });
    }

    // set visibility of .image-container to 'initial' after loading
    imageContainer.style.visibility = "initial";
    disabledArrows();
}

export { initializeSlider };
