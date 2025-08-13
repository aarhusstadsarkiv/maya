import { AutoComplete } from '/static/js/auto-complete.js';

// Updated render function to accept searchBaseUrl
const renderFunction = (data, searchBaseUrl) => {
    if (data.length == 0) return `<div class="search-suggestion-info">Ingen forslag. Tryk på søgeknappen for at fritekstsøge i stedet.</div>`;

    // Alter data
    data.forEach(item => {
        if (item.is_alt) {
            item.sub_display = `<span class="search-synonym">Synonym for: </span>${item.sub_display}`;
        }
    });

    const suggestionHelp = `<div class="search-suggestion-info">Vælg et forslag nedenfor <strong>eller</strong> tryk på søgeknappen for at fritekstsøge.</div>`;
    const suggestions = data.map(item => `
        <div class="search-suggestion-item" data-url="${searchBaseUrl}${item.search_query}=${item.id}">
            <div>
                <span class="search-icon">${item.icon}</span>
                <a href="${searchBaseUrl}${item.search_query}=${item.id}">${item.display}</a>
            </div>
            <div>${item.sub_display}</div>
        </div>`).join('');

    return `${suggestionHelp} ${suggestions}`;
};

const autocompleteElem = document.querySelector('#q');
const suggestionsElem = document.querySelector('.search-suggestions');

function autoCompleteInit(searchBaseUrl) {
    const options = {
        'autocompleteElem': autocompleteElem,
        'suggestionsElem': suggestionsElem,
        'renderFunction': (data) => renderFunction(data, searchBaseUrl), // pass searchBaseUrl
        'endpoint': `/auto_complete?q=`,
        'minInputLength': 2,
        'suggestionFocusClass': 'search-suggestion-focus',
        'preventOverflow': true,
        'overflowSpace': 20, // In pixels
        'debug': false,
    }

    new AutoComplete(options);
}

export { autoCompleteInit };
