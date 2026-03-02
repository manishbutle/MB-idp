/**
 * Admin Tab Component
 * Handles administrative credit management for System Users
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.7, 9.8
 */

/**
 * Initialize Admin tab
 */
function initAdmin() {
  // Set up event listeners
  setupAdminEventListeners();
  
  // Don't validate access on init - only validate when user tries to use admin features
  // This prevents showing error alerts when user is on other tabs
}

/**
 * Set up event listeners for Admin tab
 */
function setupAdminEventListeners() {
  // Admin credit form submission
  const adminCreditForm = document.getElementById('admin-credit-form');
  if (adminCreditForm) {
    adminCreditForm.addEventListener('submit', handleAddCredit);
  }
}

/**
 * Validate that current user has System User role
 */
async function validateAdminAccess() {
  try {
    const session = await storageManager.getSession();
    
    if (!session || !session.token) {
      // User not logged in
      return false;
    }
    
    if (!validateSystemUserRole(session)) {
      // User doesn't have System User role
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('Error validating admin access:', error);
    return false;
  }
}

/**
 * Validate if user has System User role
 * @param {Object} session - User session object
 * @returns {boolean} True if user has System User role
 */
function validateSystemUserRole(session) {
  if (!session || !session.role) {
    return false;
  }
  
  // Check if role is "System User" or "System_User"
  return session.role === 'System User' || session.role === 'System_User';
}

/**
 * Handle add credit form submission
 * @param {Event} event - Form submit event
 */
async function handleAddCredit(event) {
  event.preventDefault();
  
  // Validate admin access first
  const hasAccess = await validateAdminAccess();
  if (!hasAccess) {
    return;
  }
  
  const email = document.getElementById('admin-user-email').value.trim();
  const amount = parseFloat(document.getElementById('admin-credit-amount').value);
  
  // Validate inputs
  if (!email) {
    displayAlert('Please enter a user email address', 'error');
    return;
  }
  
  if (!amount || amount <= 0) {
    displayAlert('Please enter a valid credit amount greater than 0', 'error');
    return;
  }
  
  // Validate email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    displayAlert('Please enter a valid email address', 'error');
    return;
  }
  
  try {
    showLoading();
    
    // Call add_credit API
    const response = await apiClient.addCredit(email, amount);
    
    hideLoading();
    
    if (response.success) {
      displayAlert(`Successfully added ${amount.toFixed(2)} credits to ${email}`, 'success');
      
      // Clear form
      document.getElementById('admin-credit-form').reset();
    } else {
      // Handle specific error cases
      if (response.error === 'Forbidden' || response.error === 'Unauthorized') {
        displayAlert('Access denied. You do not have permission to add credits.', 'error');
      } else if (response.error === 'Not Found') {
        displayAlert(`User with email ${email} not found.`, 'error');
      } else {
        displayAlert(response.message || 'Failed to add credit. Please try again.', 'error');
      }
    }
  } catch (error) {
    hideLoading();
    console.error('Error adding credit:', error);
    
    // Handle specific error messages
    if (error.message.includes('Forbidden') || error.message.includes('403')) {
      displayAlert('Access denied. You do not have permission to add credits.', 'error');
    } else if (error.message.includes('Not Found') || error.message.includes('404')) {
      displayAlert(`User with email ${email} not found.`, 'error');
    } else if (error.message.includes('Bad Request') || error.message.includes('400')) {
      displayAlert('Invalid request. Please check the email and amount.', 'error');
    } else if (error.message.includes('Unauthorized') || error.message.includes('401')) {
      displayAlert('Session expired. Please log in again.', 'error');
    } else {
      displayAlert('Failed to add credit. Please try again.', 'error');
    }
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAdmin);
} else {
  initAdmin();
}
