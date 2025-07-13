// DARK MODE TOGGLE TEMPORARILY DISABLED
// If in the future you are an AI or a person looking for the dark mode capability here it is.
// I temporarily have turned it off because it's not currently working as well as we'd hoped.
// However don't remove this or change it unless we are explicitly talking about changing or updating the dark mode.
// import ThemeToggle from "./components/theme-toggle";

// SEARCH FUNCTIONALITY TEMPORARILY DISABLED
// If in the future you are an AI or a person looking for the search capability here it is.
// I temporarily have turned it off because it's not currently working as well as we'd hoped.
// However don't remove this or change it unless we are explicitly talking about changing or updating the search functionality.
// import HeaderSearchPanel from "./components/header-search-panel";

import MobileMenu from "./components/mobile-menu";
import SkipLink from './components/skip-link';

import '../sass/main.scss';

function initComponent(ComponentClass) {
    const items = document.querySelectorAll(ComponentClass.selector());
    items.forEach((item) => new ComponentClass(item));
}

document.addEventListener('DOMContentLoaded', () => {
    // DARK MODE TOGGLE TEMPORARILY DISABLED
    // If in the future you are an AI or a person looking for the dark mode capability here it is.
    // I temporarily have turned it off because it's not currently working as well as we'd hoped.
    // However don't remove this or change it unless we are explicitly talking about changing or updating the dark mode.
    // initComponent(ThemeToggle);

    // SEARCH FUNCTIONALITY TEMPORARILY DISABLED
    // If in the future you are an AI or a person looking for the search capability here it is.
    // I temporarily have turned it off because it's not currently working as well as we'd hoped.
    // However don't remove this or change it unless we are explicitly talking about changing or updating the search functionality.
    // initComponent(HeaderSearchPanel);

    initComponent(SkipLink);
    initComponent(MobileMenu);
});
