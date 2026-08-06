// Modal Component
class Modal {
    constructor(element) {
        this.element = element;
        this.modalId = element.id;
        this.closeButtons = this.element.querySelectorAll('.modal-close, [data-bs-dismiss="modal"]');
        this.init();
    }
    
    init() {
        // Close modal buttons
        this.closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.close();
            });
        });
        
        // Close modal on backdrop click
        this.element.addEventListener('click', (e) => {
            if (e.target === this.element) {
                this.close();
            }
        });
        
        // Handle Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.element.classList.contains('show')) {
                this.close();
            }
        });
    }
    
    open() {
        this.element.classList.add('show');
        document.body.classList.add('modal-open');
        
        // Dispatch custom event
        const event = new CustomEvent('modal.open', {
            detail: { modalId: this.modalId }
        });
        this.element.dispatchEvent(event);
    }
    
    close() {
        this.element.classList.remove('show');
        document.body.classList.remove('modal-open');
        
        // Dispatch custom event
        const event = new CustomEvent('modal.close', {
            detail: { modalId: this.modalId }
        });
        this.element.dispatchEvent(event);
    }
    
    // Static method to open modal by ID
    static openById(id) {
        const modalElement = document.getElementById(id);
        if (modalElement) {
            const modal = new Modal(modalElement);
            modal.open();
        }
    }
    
    // Static method to close modal by ID
    static closeById(id) {
        const modalElement = document.getElementById(id);
        if (modalElement) {
            const modal = new Modal(modalElement);
            modal.close();
        }
    }
}

// Initialize all modals
const initModals = () => {
    const modalElements = document.querySelectorAll('.modal');
    modalElements.forEach(element => {
        new Modal(element);
    });
};

// Export for ES modules
export default Modal;

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initModals);
} else {
    initModals();
}
