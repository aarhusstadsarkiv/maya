/**
 * function that serializes the error
 */
function serializeError(error) {
    // Note: level, error_type, error_code, error_url are options in the python logger
    // May use them at some point 
    let data = {
        message: error.message,
        exception: error.stack,
    };

    // Get error_url from the window object
    const error_url = window.location.href;

    // level, error_type, error_code, error_url are optional
    data.level = error.level || "ERROR";
    data.error_type = error.error_type || "Javscript Error";
    data.error_code = error.error_code || 500;
    data.error_url = error.error_url || error_url;

    console.error("Serialized error: ", data);

    return data;
}

/**
 * Send the error to the server
 * If the error is a JS error it has a stack trace and a message
 * Otherwise you may compose the error object yourself
 */
function asyncLogError(error) {

    const errorData = serializeError(error);

    // Send as json
    fetch('/error/log', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorData),
    }).then(response => {
        // Network error?
        if (!response.ok) {
            console.log("Network response was not ok")
        }

    }).catch(error => {
        // Handle the error
        console.error('There was a problem with the fetch operation:', error);
    });
}

export { asyncLogError }
