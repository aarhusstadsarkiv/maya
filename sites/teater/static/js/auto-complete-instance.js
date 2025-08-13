import { AutoComplete } from '/static/js/auto-complete.js';

function returnFunction(focusedItem) {

    // 'data-url' from focusedItem
    const url = focusedItem.getAttribute('data-url');
    if (url) {
        window.location.href = url;
        return;
    }
}

// Render function for autocomplete
const renderFunction = (data) => {

    // Info if no results
    // Tryk på søgeknappen for at fritekstsøge i stedet.
    if (data.length == 0) return `<div class="search-suggestion-info">Ingen forslag.</div>`;

    // Alter data
    data.forEach(item => {
        if (item.is_alt) {
            item.sub_display = `<span class="search-synonym">Synonym for: </span>${item.sub_display}`;
        }
    });

    // Help text and suggestions
    // <strong>eller</strong> tryk på søgeknappen for at fritekstsøge i stedet.
    const suggestionHelp = `<div class="search-suggestion-info">Vælg et forslag nedenfor.</div>`;
    
    // Suggestions
    const suggestions = data.map(item => `
        <div class="search-suggestion-item" data-url="/${item.domain}/${item.id}">
            <div>
                <span class="search-icon">${item.icon}</span>
                <a href="/${item.domain}/${item.id}">${item.display}</a>
            </div>
            <div>${item.sub_display}</div>
        </div>`).join('');

    return `${suggestionHelp} ${suggestions}`;
};

const afterRender = () => {

    // Trigger keyboard event "ArrowDown" to focus the first suggestion
    const firstSuggestion = document.querySelector('.search-suggestion-item');
    if (firstSuggestion) {
        const event = new KeyboardEvent('keydown', {
            key: 'ArrowDown',
            keyCode: 40,
            which: 40
        });
        autocompleteElem.dispatchEvent(event);
    }
}

const autocompleteElem = document.querySelector('#q');
const suggestionsElem = document.querySelector('.search-suggestions');

const options = {
    'autocompleteElem': autocompleteElem,
    'suggestionsElem': suggestionsElem,
    'renderFunction': renderFunction,
    'afterRender': afterRender,
    'endpoint': `/auto_complete?q=`,
    'minInputLength': 2,
    'suggestionFocusClass': 'search-suggestion-focus',
    'returnFunction': returnFunction,
    'preventOverflow': true,
    'overflowSpace': 20, // In pixels
    'debug': false,
}

function autoCompleteInit() {
    new AutoComplete(options);
}

document.getElementById('search').addEventListener('submit', (event) => {
    event.preventDefault();
});


export { autoCompleteInit };