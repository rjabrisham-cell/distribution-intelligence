// Navigation Component
class Navigation {
    constructor() {
        this.init();
    }
    
    init() {
        // Handle breadcrumb navigation
        this.handleBreadcrumb();
        
        // Handle back button
        this.handleBackButton();
    }
    
    handleBreadcrumb() {
        const breadcrumbLinks = document.querySelectorAll('.breadcrumb-item a');
        breadcrumbLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Optional: Add animation or loading state
                console.log('Navigating to:', link.href);
            });
        });
    }
    
    handleBackButton() {
        const backButtons = document.querySelectorAll('.btn-back-to-projects');
        backButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const target = button.getAttribute('href');
                console.log('Returning to projects:', target);
                window.location.href = target;
            });
        });
    }
    
    // Method to navigate programmatically
    navigateTo(url, options = {}) {
        const { animation = true } = options;
        
        if (animation) {
            // Add navigation animation
            document.body.classList.add('page-transition');
            setTimeout(() => {
                window.location.href = url;
            }, 300);
        } else {
            window.location.href = url;
        }
    }
}

// Export for ES modules
export default Navigation;

// Initialize navigation
const initNavigation = () => {
    new Navigation();
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNavigation);
} else {
    initNavigation();
}
