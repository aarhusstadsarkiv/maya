/**
 * Get a Path segment of the window.location.pathname
 */
function getPathPart(num, path) {
    if (!path) {
        path = window.location.pathname;
    }
    var ary = path.split('/');
    ary.shift();
    return ary[num];
}

function isLikelyPhoneDevice() {
    if (navigator.userAgentData && typeof navigator.userAgentData.mobile === 'boolean') {
        return navigator.userAgentData.mobile;
    }

    const userAgent = navigator.userAgent || '';
    return /(iPhone|iPod|Android.*Mobile|Windows Phone|Mobile)/i.test(userAgent);
}


export { getPathPart, isLikelyPhoneDevice };