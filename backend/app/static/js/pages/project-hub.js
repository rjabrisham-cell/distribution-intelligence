import Dropdown from '../components/dropdown.js';
import Navigation from '../components/navigation.js';
import Modal from '../components/modal.js';

// Project Hub Page Controller
class ProjectHubPage {
    constructor() {
        this.init();
    }
    
    init() {
        // Initialize components
        this.initComponents();
        
        // Initialize page-specific functionality
        this.initPageFeatures();
        
        // Handle RTL/LTR
        this.handleDirection();
        
        // Log page load
        console.log('Project Hub page initialized');
    }
    
    initComponents() {
        // Components are already initialized via their own scripts
        // This is for page-specific component configuration
    }
    
    initPageFeatures() {
        // Handle more actions dropdown
        this.handleMoreActions();
        
        // Handle journey stepper animation
        this.handleJourneyAnimation();
        
        // Handle current step highlight
        this.handleCurrentStep();
    }
    
    handleMoreActions() {
        const moreActionsBtn = document.querySelector('.btn-more-actions');
        if (moreActionsBtn) {
            moreActionsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                // Already handled by Dropdown component
            });
        }
    }
    
    handleJourneyAnimation() {
        const journeySteps = document.querySelectorAll('.step-container');
        journeySteps.forEach((step, index) => {
            step.addEventListener('mouseenter', () => {
                step.classList.add('step-hover');
            });
            
            step.addEventListener('mouseleave', () => {
                step.classList.remove('step-hover');
            });
        });
    }
    
    handleCurrentStep() {
        const currentStep = document.querySelector('.step-container.active-step');
        if (currentStep) {
            // Add subtle pulse animation to current step
            currentStep.classList.add('step-pulse');
        }
    }
    
    handleDirection() {
        const dir = document.documentElement.dir || 'ltr';
        const html = document.documentElement;
        
        if (dir === 'rtl') {
            html.classList.add('rtl');
            html.classList.remove('ltr');
        } else {
            html.classList.add('ltr');
            html.classList.remove('rtl');
        }
        
        // Watch for direction changes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'dir') {
                    this.handleDirection();
                }
            });
        });
        
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['dir']
        });
    }
    
    // Page-specific method to open data intake
    openDataIntake() {
        const openBtn = document.querySelector('.btn-primary-action');
        if (openBtn) {
            openBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const url = openBtn.getAttribute('href');
                console.log('Opening Data Intake:', url);
                
                // Optional: Add loading state
                openBtn.classList.add('loading');
                openBtn.innerHTML = 'Loading...';
                
                setTimeout(() => {
                    window.location.href = url;
                }, 500);
            });
        }
    }
}

// Initialize Project Hub page
document.addEventListener('DOMContentLoaded', () => {
    new ProjectHubPage();
});

export default ProjectHubPage;
