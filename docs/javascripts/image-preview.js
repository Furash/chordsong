/**
 * Image Preview Modal
 * Opens images in a modal overlay when clicked
 */

(function() {
    'use strict';

    // Create modal elements
    const modal = document.createElement('div');
    modal.id = 'image-preview-modal';
    modal.style.cssText = `
        display: none;
        position: fixed;
        z-index: 10000;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.9);
        cursor: pointer;
        align-items: center;
        justify-content: center;
    `;

    const modalImg = document.createElement('img');
    modalImg.style.cssText = `
        max-width: 90%;
        max-height: 90%;
        object-fit: contain;
        margin: auto;
        display: block;
    `;

    const closeBtn = document.createElement('span');
    closeBtn.innerHTML = '&times;';
    closeBtn.style.cssText = `
        position: absolute;
        top: 15px;
        right: 35px;
        color: #f1f1f1;
        font-size: 40px;
        font-weight: bold;
        cursor: pointer;
        z-index: 10001;
    `;
    closeBtn.addEventListener('mouseover', function() {
        this.style.color = '#bbb';
    });
    closeBtn.addEventListener('mouseout', function() {
        this.style.color = '#f1f1f1';
    });

    modal.appendChild(closeBtn);
    modal.appendChild(modalImg);
    document.body.appendChild(modal);

    // Function to open modal
    function openModal(imgSrc) {
        modal.style.display = 'flex';
        modalImg.src = imgSrc;
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    // Function to close modal
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
    }

    // Close modal when clicking on it or the close button
    modal.addEventListener('click', function(e) {
        if (e.target === modal || e.target === closeBtn) {
            closeModal();
        }
    });

    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            closeModal();
        }
    });

    // Add click handlers to all images in the content area
    function attachImageHandlers() {
        // Find all images in the main content area (excluding logo/nav images)
        const contentArea = document.querySelector('.md-content') || document.querySelector('main') || document.body;
        const images = contentArea.querySelectorAll('img');

        images.forEach(function(img) {
            // Skip if already has click handler
            if (img.dataset.previewAttached) {
                return;
            }

            // Skip logo and navigation images
            const src = img.src || img.getAttribute('src') || '';
            if (src.includes('logo') || img.closest('nav') || img.closest('.md-header')) {
                return;
            }

            // Add cursor pointer style
            img.style.cursor = 'pointer';

            // Add click handler
            img.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const imgSrc = this.src || this.getAttribute('src');
                if (imgSrc) {
                    openModal(imgSrc);
                }
            });

            // Mark as attached
            img.dataset.previewAttached = 'true';
        });
    }

    // Attach handlers when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachImageHandlers);
    } else {
        attachImageHandlers();
    }

    // Re-attach handlers when content changes (for SPA navigation in Material theme)
    if (typeof mermaid !== 'undefined' || document.querySelector('.md-content')) {
        const observer = new MutationObserver(function(mutations) {
            attachImageHandlers();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
})();
