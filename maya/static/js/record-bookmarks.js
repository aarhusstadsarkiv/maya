// script to be used on record page to add or remove bookmarks
import { asyncLogError } from "/static/js/error.js";
import { Requests } from "/static/js/requests.js";
import { Flash } from "/static/js/flash.js";
import { config } from "/static/js/config.js";

let action;
const bookmarkAddElem = document.getElementById('bookmark-action');
if (bookmarkAddElem) {
    const recordId = bookmarkAddElem.getAttribute('data-id');
    const spinner = document.querySelector('.loadingspinner');

    /**
     * Load bookmarks
     * Initialize bookmark button
     */
    const initialize = async () => {
        const url = `/auth/bookmarks/json?record_id=${recordId}`;
        let bookmarksJSON = await Requests.asyncGetJson(url, 'GET');
        if (Object.keys(bookmarksJSON).length !== 0) {
            bookmarkAddElem.innerHTML = 'Fjern bogmærke';
            action = 'delete';
            bookmarkAddElem.setAttribute('data-action', action);
            bookmarkAddElem.classList.add('delete-bookmark')
        } else {
            bookmarkAddElem.innerHTML = 'Tilføj bogmærke';
            action = 'add';
            bookmarkAddElem.setAttribute('data-action', action);
            bookmarkAddElem.classList.remove('delete-bookmark')
        }
    }

    await initialize();

    /**
     * Get data for record to be bookmarked
     */
    const get_data = () => {
        const data = { record_id: recordId, action: action };
        return JSON.stringify(data);
    }

    /**
     * Add or remove bookmark
     */
    bookmarkAddElem.addEventListener('click', async function (e) {
        let res;
        e.preventDefault();
        spinner.classList.toggle('hidden');
        try {
            const data = get_data();
            res = await Requests.asyncPostJson('/auth/bookmarks', data, 'POST');
            if (res.error) {
                Flash.setMessage(res.message, 'error');
            } else {
                Flash.setMessage(res.message, 'success');
            }
        } catch (e) {
            Flash.setMessage(config.jsExceptionMessage, 'error');
            asyncLogError(e);
            console.error(e);
        } finally {
            initialize();
            spinner.classList.toggle('hidden');
        }
    });
}


