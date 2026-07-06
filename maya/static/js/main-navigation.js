const hamburgerMenu = document.getElementById('menu-hamburger');
const openMenu = hamburgerMenu.querySelector('.open');
const closedMenu = hamburgerMenu.querySelector('.closed');
const menu = document.querySelector('.main-menu-overlay');
const dropdowns = Array.from(document.querySelectorAll('.menu-dropdown'));

function closeDropdown(dropdown, restoreFocus = false) {
    const toggle = dropdown.querySelector('.menu-dropdown-toggle');
    const list = dropdown.querySelector('.menu-dropdown-list');

    list.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');

    if (restoreFocus) {
        toggle.focus();
    }
}

function closeAllDropdowns(except = null) {
    dropdowns.forEach(dropdown => {
        if (dropdown !== except) {
            closeDropdown(dropdown);
        }
    });
}

dropdowns.forEach(dropdown => {
    const toggle = dropdown.querySelector('.menu-dropdown-toggle');
    const list = dropdown.querySelector('.menu-dropdown-list');

    toggle.addEventListener('click', function () {
        const shouldOpen = list.hidden;
        closeAllDropdowns(dropdown);
        list.hidden = !shouldOpen;
        toggle.setAttribute('aria-expanded', String(shouldOpen));
    });

    dropdown.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !list.hidden) {
            event.preventDefault();
            closeDropdown(dropdown, true);
        }
    });
});

hamburgerMenu.addEventListener('click', function (event) {
    event.preventDefault();

    // Expand
    if (menu.style.display === "none" || menu.style.display === "") {
        menu.style.display = "block";
        openMenu.style.display = "block";
        closedMenu.style.display = "none";
        hamburgerMenu.setAttribute('aria-expanded', 'true');
    } else {
        menu.style.display = "none";
        openMenu.style.display = "none";
        closedMenu.style.display = "block";
        hamburgerMenu.setAttribute('aria-expanded', 'false');
    }
});

document.addEventListener('click', function (event) {
    if (!hamburgerMenu.contains(event.target) && !menu.contains(event.target)) {
        menu.style.display = "none";
        openMenu.style.display = "none";
        closedMenu.style.display = "block";
        hamburgerMenu.setAttribute('aria-expanded', 'false');
    }

    dropdowns.forEach(dropdown => {
        if (!dropdown.contains(event.target)) {
            closeDropdown(dropdown);
        }
    });
});

// on pageshow event, if the menu is open, close it
window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
        menu.style.display = "none";
        openMenu.style.display = "none";
        closedMenu.style.display = "block";
        hamburgerMenu.setAttribute('aria-expanded', 'false');
        closeAllDropdowns();
    }
});

const actionLinks = document.querySelectorAll('.action-links > a');
let activeLinkSet = false;

actionLinks.forEach(link => {
    const path = link.getAttribute('data-path') || link.getAttribute('href');
    const isExactMatch = path === window.location.pathname;
    const isPartialMatch = path !== '/' && window.location.pathname.startsWith(path);

    if (isExactMatch || isPartialMatch) {
        link.classList.add('active');
        activeLinkSet = true;
    }
});

// Same as above but for .sub-menu
const subMenuLinks = document.querySelectorAll('.sub-menu a');
subMenuLinks.forEach(link => {
    const path = link.getAttribute('data-path') || link.getAttribute('href');
    const isExactMatch = path === window.location.pathname;
    const isPartialMatch = path !== '/' && window.location.pathname.startsWith(path);

    if (isExactMatch || isPartialMatch) {
        link.classList.add('active');
        activeLinkSet = true;
    }
});
