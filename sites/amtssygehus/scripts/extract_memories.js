// Extracting data from salling erindringer. 

// E.g. https://sallingarkivet.dk/erindringer/hanne-i-tagrestaurant-og-kundeservice-1963-66
// Copy and paste this code into the browser console on the page above. 
// Copy the object that and paste where you need it.

function extractContent() {
    let container = document.querySelector('.intro');
    
    if (!container) return null;
    
    let heading = container.querySelector('h1')?.innerText || '';
    let paragraphs = Array.from(container.querySelectorAll('p')).map(p => p.innerText);

    const items = document.querySelectorAll('[item="item"]');
    const ids = Array.from(items).map(item => {
        const firstItemDiv = item.querySelector('div.item');
        if (firstItemDiv) {
            return firstItemDiv.id.replace(/^item-/, '');
        }
        return null;
    }).filter(id => id !== null);

    const recordIds = [...new Set(ids)];
    
    return {
        heading,
        paragraphs,
        recordIds: recordIds
    };
}

// Example usage:
let extractedData = extractContent();
console.log(extractedData);
