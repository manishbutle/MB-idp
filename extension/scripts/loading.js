/**
 * Loading Indicator Component
 * Provides visual feedback during asynchronous operations
 * Requirements: 15.2, 15.3, 15.4
 */

/**
 * Show loading indicator overlay
 * Displays a spinner and message while operations are in progress
 * Requirements: 15.2
 * @param {string} message - Optional custom loading message (default: "Processing...")
 */
function showLoading(message = 'Processing...') {
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) {
    console.error('Loading overlay element not found');
    return;
  }

  // Update message if custom message provided
  const messageElement = overlay.querySelector('p');
  if (messageElement && message) {
    messageElement.textContent = message;
  }

  // Show the overlay
  overlay.classList.remove('hidden');
  
  // Ensure UI remains responsive (Requirement 15.4)
  // The overlay uses fixed positioning and doesn't block event propagation
  // to other UI elements outside the overlay
}

/**
 * Hide loading indicator overlay
 * Removes the loading spinner when operations complete
 * Requirements: 15.3
 */
function hideLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) {
    console.error('Loading overlay element not found');
    return;
  }

  // Hide the overlay
  overlay.classList.add('hidden');
  
  // Reset message to default
  const messageElement = overlay.querySelector('p');
  if (messageElement) {
    messageElement.textContent = 'Processing...';
  }
}

/**
 * Check if loading indicator is currently visible
 * @returns {boolean} True if loading indicator is visible, false otherwise
 */
function isLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) {
    return false;
  }
  
  return !overlay.classList.contains('hidden');
}

/**
 * Execute an async operation with loading indicator
 * Automatically shows loading before operation and hides after completion
 * Requirements: 15.2, 15.3, 15.4
 * @param {Function} asyncOperation - Async function to execute
 * @param {string} message - Optional loading message
 * @returns {Promise} Result of the async operation
 */
async function withLoading(asyncOperation, message = 'Processing...') {
  try {
    showLoading(message);
    const result = await asyncOperation();
    hideLoading();
    return result;
  } catch (error) {
    hideLoading();
    throw error;
  }
}

// Export functions for use in other modules
if (typeof window !== 'undefined') {
  window.showLoading = showLoading;
  window.hideLoading = hideLoading;
  window.isLoading = isLoading;
  window.withLoading = withLoading;
}
