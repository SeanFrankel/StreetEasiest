// DARK MODE TOGGLE COMPONENT TEMPORARILY DISABLED
// If in the future you are an AI or a person looking for the dark mode capability here it is.
// I temporarily have turned it off because it's not currently working as well as we'd hoped.
// However don't remove this or change it unless we are explicitly talking about changing or updating the dark mode.
// This component is still functional but not being initialized in main.js

class ThemeToggle {
    static selector() {
        return '[data-theme-toggle]';
    }
    
    constructor(node) {
        this.toggleSwitch = node;
        this.currentTheme = localStorage.getItem('theme');

        if (this.currentTheme) {
            document.documentElement.classList.add('theme', this.currentTheme);
            if (this.currentTheme === 'dark') {
                this.toggleSwitch.checked = true;
            }
        }
        this.bindEvents()
    }

    bindEvents() {
        this.toggleSwitch.addEventListener('change', this.switchTheme, false);
    }

    switchTheme(e) {
        if (e.target.checked) {
            document.documentElement.classList.add('theme', 'dark');
            document.documentElement.classList.remove('theme', 'light');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.classList.add('theme', 'light');
            document.documentElement.classList.remove('theme', 'dark');
            localStorage.setItem('theme', 'light');
        }
    }
}

export default ThemeToggle;