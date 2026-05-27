import { asyncLogError } from "/static/js/error.js";

const imgSrcDirectives = ["img-src", "img-src-elem"];
const loggedImageErrors = new Set();
const imageErrorMessage = "Missing Image Error";

function getImageUrl(img) {
    return img.currentSrc || img.src || img.getAttribute('src') || "";
}

function shouldIgnoreImage(img) {
    return img.getAttribute('loading') === 'lazy';
}

function logImageError(missingImageUrl) {
    if (!missingImageUrl || loggedImageErrors.has(missingImageUrl)) {
        return;
    }
    loggedImageErrors.add(missingImageUrl);

    let error = new Error(`${imageErrorMessage}: ${missingImageUrl}`);

    // Set current page url
    error.error_url = window.location.href;
    error.error_code = 404;
    error.error_type = imageErrorMessage;

    asyncLogError(error);
}

const images = document.querySelectorAll('img');
images.forEach((img) => {
    img.onerror = async () => {

        // If image attribute loading equals "lazy" loaded ignore it
        if (shouldIgnoreImage(img)) {
            return;
        }

        logImageError(getImageUrl(img));

    };

    if (!shouldIgnoreImage(img) && img.complete && img.naturalWidth === 0) {
        logImageError(getImageUrl(img));
    }
});

document.addEventListener("securitypolicyviolation", (event) => {
    if (!imgSrcDirectives.includes(event.effectiveDirective)) {
        return;
    }

    logImageError(event.blockedURI);
}, true);
