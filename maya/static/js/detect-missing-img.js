import { asyncLogError } from "/static/js/error.js";

const imgSrcDirectives = ["img-src", "img-src-elem"];
const loggedImageErrors = new Set();
const imageErrorMessage = "Missing Image Error";

function getImageUrl(img) {
    return img.currentSrc || img.src || img.getAttribute('src') || "";
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
    error.level = "WARNING";

    asyncLogError(error);
}

function logIfImageIsMissing(img) {
    if (img.complete && img.naturalWidth === 0) {
        logImageError(getImageUrl(img));
    }
}

document.addEventListener("error", (event) => {
    if (event.target instanceof HTMLImageElement) {
        logImageError(getImageUrl(event.target));
    }
}, true);

document.querySelectorAll("img").forEach(logIfImageIsMissing);

document.addEventListener("securitypolicyviolation", (event) => {
    if (!imgSrcDirectives.includes(event.effectiveDirective)) {
        return;
    }

    logImageError(event.blockedURI);
}, true);
