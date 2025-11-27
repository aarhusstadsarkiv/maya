import { Events } from '/static/js/events.js';
import { Flash } from '/static/js/flash.js';
import { asyncLogError } from '/static/js/error.js';
import { truncateText } from '/static/js/truncate-text.js';
import { config } from '/static/js/config.js';
import jsCookie from '/static/js/js-cookie.js';

const containerLeft = document.querySelector('.container-left');
const containerMainFacets = document.querySelector('.container-main-facets');

/**
 * Utility function to save the state of details elements from a given container
 */
function saveState(containerSelector, storageKey) {
    const openFacets = [];
    const detailsElements = document.querySelectorAll(`${containerSelector} .facets details`);

    detailsElements.forEach(detailElement => {
        if (detailElement.open) {
            openFacets.push(detailElement.getAttribute('data-id'));
        }
    });

    jsCookie.set(storageKey, JSON.stringify(openFacets));
}

/**
 * Save the state of the tree to local storage
 */
function saveTree() {
    
    if (containerLeft) {
        if (window.getComputedStyle(containerLeft).display != 'none') {
            saveState('.container-left', 'treeState');
        }
    }
    
    if (containerMainFacets) {
        if (window.getComputedStyle(containerMainFacets).display != 'none') {
            saveState('.container-main-facets', 'treeState');
        }
    }
}

/**
 * Utility function to expand tree from saved state
 */
function expandTreeFromState(containerSelector, storageKey) {

    const cookieStorageKey = jsCookie.get(storageKey);
    if (cookieStorageKey) {

        const openFacets = JSON.parse(jsCookie.get(storageKey));
        if (openFacets && openFacets.length) {
            const detailElements = document.querySelectorAll(`${containerSelector} .facets details`);
            detailElements.forEach(detailElement => {
                if (openFacets.includes(detailElement.getAttribute('data-id'))) {
                    detailElement.open = true;
                }
            });
        }
    }
}

/**
 * Expands the tree based on the saved state from local storage
 */
function expandTree() {

    if (containerLeft) {
        if (window.getComputedStyle(containerLeft).display != 'none') {
            expandTreeFromState('.container-left', 'treeState');
        }
    }

    if (containerMainFacets) {
        if (window.getComputedStyle(containerMainFacets).display != 'none') {
            expandTreeFromState('.container-main-facets', 'treeState');
        }
    }
}

document.querySelectorAll('.facets-clickable').forEach(facet => {
    facet.addEventListener('click', function (e) {
        // The tree needs time to be updated before saving the state
        setTimeout(() => {
            saveTree();
        }, 100);
    });
});

/**
 * Check if a string is a valid date
 */
function isValidDate(dateString) {

    // Parse the input string as yyyy-mm-dd
    const dateParts = dateString.split("-");
    const year = parseInt(dateParts[0], 10);
    const month = parseInt(dateParts[1], 10);
    const day = parseInt(dateParts[2], 10);

    // Create a new Date object using the parsed values
    const date = new Date(year, month - 1, day);

    // Check if the parsed date is valid
    return (
        date.getFullYear() === year &&
        date.getMonth() === month - 1 &&
        date.getDate() === day
    );
}

/**
 * Search form submit event
 */
function onSearchDateEvent(dateFormClass) {
    const searchDateElem = document.querySelector(dateFormClass);
    if (!searchDateElem) {
        return;
    }

    searchDateElem.addEventListener('submit', function (e) {
        e.preventDefault();

        const fromYear = document.querySelector(`${dateFormClass} .from-year`).value;
        const fromMonth = document.querySelector(`${dateFormClass} .from-month`).value || '01';
        const fromDay = document.querySelector(`${dateFormClass} .from-day`).value || '01';
        const toYear = document.querySelector(`${dateFormClass} .to-year`).value;
        const toMonth = document.querySelector(`${dateFormClass} .to-month`).value || '12';
        const toDay = document.querySelector(`${dateFormClass} .to-day`).value || '31';

        if (!fromYear && !toYear) {
            Flash.setMessage('Du skal indtaste en dato mellem 1200 og aktuel data', 'error');
            return;
        }

        // One date has been entered now
        const fromDate = `${fromYear}-${fromMonth}-${fromDay}`;
        const toDate = `${toYear}-${toMonth}-${toDay}`;

        if (toYear && !isValidDate(toDate)) {
            Flash.setMessage('Til dato er ikke gyldig', 'error');
            return;
        }

        if (fromYear && !isValidDate(fromDate)) {
            Flash.setMessage('Fra dato er ikke gyldig', 'error');
            return;
        }

        // Redirect to new url and add date_from and date_to to url
        const url = window.location.href;
        const urlParams = new URLSearchParams(window.location.search);
        
        if (isValidDate(fromDate)) {
            urlParams.set('date_from', `${fromYear}${fromMonth}${fromDay}`);
        }
        if (isValidDate(toDate)) {
            urlParams.set('date_to', `${toYear}${toMonth}${toDay}`);
        }

        // Reset start parameter
        urlParams.delete('start');

        window.location.href = url.split('?')[0] + '?' + urlParams.toString();
    });
}


/**
 * Expand tree based on saved state
 */
function searchEvents() {

    try {

        const facetsToogle = document.getElementById('facets-toggle');
        let hideFacetsState = jsCookie.get('hideFacets') || 'true';

        const hideFacetsElement = () => {
            containerMainFacets.style.display = 'none';
            if (facetsToogle) facetsToogle.textContent = 'Vis filtre';
        }

        const showFacetsElements = () => {
            containerMainFacets.style.display = 'block';
            if (facetsToogle) facetsToogle.textContent = 'Skjul filtre';
        }

        const initFacetsElements = () => {
            if (hideFacetsState === 'true') {
                hideFacetsElement();
            } else {
                showFacetsElements();
            }
        }

        initFacetsElements();

        facetsToogle?.addEventListener('click', function (e) {
            e.preventDefault();
            if (containerMainFacets.style.display === 'none') {
                hideFacetsState = 'false';
                showFacetsElements();
                jsCookie.set('hideFacets', 'false');
            } else {
                hideFacetsState = 'true';
                hideFacetsElement();
                jsCookie.set('hideFacets', 'true');
            }
        });

        let lastWindowWidth = window.innerWidth;

        function onResize() {
            const currentWindowWidth = window.innerWidth;

            // Check if the resize event crosses the 992px to 993px boundary
            if ((lastWindowWidth <= 992 && currentWindowWidth > 992) || (lastWindowWidth > 992 && currentWindowWidth <= 992)) {
                expandTree();
                truncateText(document.querySelectorAll(".search-summary"), 80, true);
            }

            if (currentWindowWidth > 992) {
                hideFacetsElement();
                truncateText(document.querySelectorAll(".search-summary"), 80, false);
            }

            if (currentWindowWidth <= 992) {
                initFacetsElements();
                truncateText(document.querySelectorAll(".search-summary"), 80, true);
            }

            // Update the last window width for the next resize event
            lastWindowWidth = currentWindowWidth;

        }

        window.addEventListener('resize', () => {
            onResize();
        });

        onResize();
        expandTree();

        // Two date search forms on search page
        onSearchDateEvent('.search-date');
        onSearchDateEvent('.search-date-main');

        // Ensure only numbers can be entered in the date fields
        Events.addEventListenerMultiple('.search-date > input', 'input', function (e) {
            const input = e.target;
            input.value = input.value.replace(/\D/g, '');
        });

        Events.addEventListenerMultiple('.search-date-main > input', 'input', function (e) {
            const input = e.target;
            input.value = input.value.replace(/\D/g, '');
        });

        // Also add event listener to search form with id 'search-date'
        const searchElem = document.getElementById('q');
        searchElem.addEventListener('submit', function (e) {
            e.preventDefault();
            searchElem.submit();
        })

        const selectSize = document.querySelector('.select-size');
        selectSize.addEventListener('change', function () {
            document.getElementById('size').submit();
        });

        const selectView = document.querySelector('.select-view');
        selectView.addEventListener('change', function () {
            document.getElementById('view').submit();
        });

        const selectSort = document.querySelector('.select-sort');
        selectSort.addEventListener('change', function () {

            const selectedValue = selectSort.value;
            if (selectedValue == 'date_to') {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'direction';
                input.value = 'desc';
                document.getElementById('sort').appendChild(input);
            }

            if (selectedValue == 'date_from') {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'direction';
                input.value = 'asc';
                document.getElementById('sort').appendChild(input);
            }
            document.getElementById('sort').submit();
        });

        // Focus on search input field
        // Only if not on mobile device
        // if (window.innerWidth > config.mobileWidth) {
        //     document.getElementById('q').focus();
        // }
        // document.getElementById('q').focus();

    } catch (error) {
        console.log(error)
        // unset local storage if it fails. 
        // The tree may be updated and the saved state may be invalid
        jsCookie.remove('treeState');
        asyncLogError(error);

    }
}

export { searchEvents }


/**
 *  Utility function to collapse all details elements in a given container
 */
// function collapseTree(containerSelector) {
//     const detailsElements = document.querySelectorAll(`${containerSelector} .facets details`);
//     detailsElements.forEach(detailElement => {
//         detailElement.open = false;
//     });
// }

/**
 * Collapses all trees
 */
// function collapseAllTrees() {
//     collapseTree('.container-main-facets');
// }
