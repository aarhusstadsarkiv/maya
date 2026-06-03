const validThemes = ['light', 'dark'];

const themeLink = document.getElementById('theme-stylesheet');
const themeToggle = document.getElementById('theme-toggle');

if (themeLink && themeToggle) {
    const lightIcon = themeToggle.querySelector('.theme-toggle-icon-light');
    const darkIcon = themeToggle.querySelector('.theme-toggle-icon-dark');
    initializeThemeSwitcher(lightIcon, darkIcon);
}

function getCurrentTheme() {
    return themeLink.getAttribute('href') === themeLink.dataset.darkHref ? 'dark' : 'light';
}

function setTheme(theme, lightIcon, darkIcon) {
    if (!validThemes.includes(theme)) {
        return;
    }

    const href = theme === 'dark' ? themeLink.dataset.darkHref : themeLink.dataset.lightHref;
    themeLink.setAttribute('href', href);
    document.documentElement.dataset.theme = theme;

    themeToggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    themeToggle.setAttribute(
        'aria-label',
        theme === 'dark' ? themeToggle.dataset.lightLabel : themeToggle.dataset.darkLabel,
    );

    if (lightIcon && darkIcon) {
        lightIcon.hidden = theme === 'light';
        darkIcon.hidden = theme === 'dark';
    }
}

async function persistTheme(theme) {
    const data = {
        cookie_name: 'dark_theme',
        cookie_value: theme === 'dark',
    };

    const response = await fetch('/auth/cookie', {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        throw new Error('Theme preference could not be saved.');
    }
}

function initializeThemeSwitcher(lightIcon, darkIcon) {
    setTheme(getCurrentTheme(), lightIcon, darkIcon);

    themeToggle.addEventListener('click', async function () {
        const previousTheme = getCurrentTheme();
        const nextTheme = getCurrentTheme() === 'dark' ? 'light' : 'dark';

        setTheme(nextTheme, lightIcon, darkIcon);

        try {
            await persistTheme(nextTheme);
        } catch {
            setTheme(previousTheme, lightIcon, darkIcon);
        }
    });
}
