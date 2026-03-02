/**
 * Alert/Notification System
 * Provides user feedback for operations (success, error, warning)
 * Requirements: 14.1, 14.2, 14.3, 14.8
 */

/**
 * Display an alert message to the user
 * @param {string} message - The message to display
 * @param {string} type - The alert type: 'success', 'error', or 'warning'
 */
function displayAlert(message, type = 'info') {
  const container = document.getElementById('alert-container');
  if (!container) {
    console.error('Alert container not found');
    return;
  }

  // Create alert element
  const alert = document.createElement('div');
  alert.className = `alert alert-${type} flex items-center justify-between p-4 rounded-lg shadow-lg mb-2 min-w-[300px] max-w-[500px] animate-slide-in`;
  
  // Set background and text colors based on type
  const styles = {
    success: 'bg-green-100 border-l-4 border-green-500 text-green-800',
    error: 'bg-red-100 border-l-4 border-red-500 text-red-800',
    warning: 'bg-yellow-100 border-l-4 border-yellow-500 text-yellow-800',
    info: 'bg-blue-100 border-l-4 border-blue-500 text-blue-800'
  };
  
  alert.className += ` ${styles[type] || styles.info}`;
  
  // Get icon based on type
  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  };
  
  // Create alert content
  alert.innerHTML = `
    <div class="flex items-center">
      <span class="text-2xl mr-3">${icons[type] || icons.info}</span>
      <span class="font-medium">${escapeHtml(message)}</span>
    </div>
    <button class="alert-close ml-4 text-xl font-bold opacity-70 hover:opacity-100 transition-opacity" aria-label="Close">
      &times;
    </button>
  `;
  
  // Add to container
  container.appendChild(alert);
  
  // Add close button functionality
  const closeBtn = alert.querySelector('.alert-close');
  closeBtn.addEventListener('click', () => {
    removeAlert(alert);
  });
  
  // Auto-dismiss success alerts after 3 seconds (Requirement 14.2)
  if (type === 'success') {
    setTimeout(() => {
      removeAlert(alert);
    }, 3000);
  }
  
  // Auto-dismiss other alerts after 5 seconds
  if (type !== 'success') {
    setTimeout(() => {
      removeAlert(alert);
    }, 5000);
  }
}

/**
 * Remove an alert with fade-out animation
 * @param {HTMLElement} alert - The alert element to remove
 */
function removeAlert(alert) {
  if (!alert || !alert.parentNode) return;
  
  // Add fade-out animation
  alert.style.opacity = '0';
  alert.style.transform = 'translateX(100%)';
  alert.style.transition = 'all 0.3s ease-out';
  
  // Remove from DOM after animation
  setTimeout(() => {
    if (alert.parentNode) {
      alert.parentNode.removeChild(alert);
    }
  }, 300);
}

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - The text to escape
 * @returns {string} - The escaped text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Clear all alerts from the container
 */
function clearAllAlerts() {
  const container = document.getElementById('alert-container');
  if (container) {
    container.innerHTML = '';
  }
}

// Export functions for use in other modules
if (typeof window !== 'undefined') {
  window.displayAlert = displayAlert;
  window.removeAlert = removeAlert;
  window.clearAllAlerts = clearAllAlerts;
}
