// Dropdown Component
class Dropdown {
    constructor(element) {
        this.element = element;
        this.toggle = this.element.querySelector('.dropdown-toggle');
        this.menu = this.element.querySelector('.dropdown-menu');
        this.init();
    }
    
    init() {
        if (!this.toggle || !this.menu) return;
        
        this.toggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.toggleMenu();
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.element.contains(e.target)) {
                this.closeMenu();
            }
        });
    }
    
    toggleMenu() {
        if (this.menu.classList.contains('show')) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }
    
    openMenu() {
        this.menu.classList.add('show');
        this.toggle.setAttribute('aria-expanded', 'true');
    }
    
    closeMenu() {
        this.menu.classList.remove('show');
        this.toggle.setAttribute('aria-expanded', 'false');
    }
}

// Initialize all dropdowns
const initDropdowns = () => {
    const dropdownElements = document.querySelectorAll('.dropdown');
    dropdownElements.forEach(element => {
        new Dropdown(element);
    });
};

// Export for ES modules
export default Dropdown;

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDropdowns);
} else {
    initDropdowns();
}
