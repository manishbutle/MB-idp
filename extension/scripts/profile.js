/**
 * Profile Tab Component
 * Handles user authentication, profile management, and account operations
 */

// State management
let isLoggedIn = false;
let currentUser = null;
let currentTransactionPage = 1;
let totalTransactionPages = 1;

/**
 * Initialize Profile tab
 */
function initProfile() {
  // Check if user is already logged in
  checkAuthStatus();
  
  // Set up event listeners
  setupProfileEventListeners();
}

/**
 * Callback when Profile tab becomes visible
 * Called by popup.js when user switches to Profile tab
 * Refreshes all data on the profile page
 */
window.onProfileTabVisible = async function() {
  console.log('[Profile] Tab became visible, refreshing all data');
  try {
    const session = await storageManager.getSession();
    if (session && session.token) {
      // Refresh all profile data
      await loadProfile();
      console.log('[Profile] All data refreshed successfully');
    } else {
      console.log('[Profile] User not logged in, skipping data refresh');
    }
  } catch (error) {
    console.error('[Profile] Error refreshing data on tab visible:', error);
  }
};

/**
 * Check authentication status on load
 */
async function checkAuthStatus() {
  try {
    const session = await storageManager.getSession();
    
    if (session && session.token) {
      // Validate token is not expired
      if (session.expires_at && new Date(session.expires_at) > new Date()) {
        isLoggedIn = true;
        currentUser = session;
        showLoggedInView();
      } else {
        // Token expired, clear session
        await clearSession();
        showLoggedOutView();
      }
    } else {
      showLoggedOutView();
    }
  } catch (error) {
    console.error('Error checking auth status:', error);
    showLoggedOutView();
  }
}

/**
 * Set up event listeners for Profile tab
 */
function setupProfileEventListeners() {
  // Login form
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }
  
  // Forget password link
  const forgetPasswordLink = document.getElementById('forget-password-link');
  if (forgetPasswordLink) {
    forgetPasswordLink.addEventListener('click', handleForgetPassword);
  }
  
  // Sign up link
  const signupLink = document.getElementById('signup-link');
  if (signupLink) {
    signupLink.addEventListener('click', handleSignup);
  }

  // Logout link
  const logoutLink = document.getElementById('logout-link');
  if (logoutLink) {
    logoutLink.addEventListener('click', handleLogout);
  }

  // Profile settings toggle
  const profileSettingsToggle = document.getElementById('profile-settings-toggle');
  if (profileSettingsToggle) {
    profileSettingsToggle.addEventListener('click', toggleProfileSettings);
  }

  // Change password toggle
  const changePasswordToggle = document.getElementById('change-password-toggle');
  if (changePasswordToggle) {
    changePasswordToggle.addEventListener('click', toggleChangePassword);
  }

  // Transaction history toggle
  const transactionHistoryToggle = document.getElementById('transaction-history-toggle');
  if (transactionHistoryToggle) {
    transactionHistoryToggle.addEventListener('click', toggleTransactionHistory);
  }

  // Save profile button
  const saveProfileBtn = document.getElementById('save-profile-btn');
  if (saveProfileBtn) {
    saveProfileBtn.addEventListener('click', handleSaveProfile);
  }

  // Change password button
  const changePasswordBtn = document.getElementById('change-password-btn');
  if (changePasswordBtn) {
    changePasswordBtn.addEventListener('click', handleChangePassword);
  }

  // Top-up button
  const topupBtn = document.getElementById('topup-btn');
  if (topupBtn) {
    topupBtn.addEventListener('click', handleTopup);
  }

  // Transaction pagination
  const transactionPrevBtn = document.getElementById('transaction-prev-btn');
  const transactionNextBtn = document.getElementById('transaction-next-btn');
  if (transactionPrevBtn) {
    transactionPrevBtn.addEventListener('click', () => loadTransactions(currentTransactionPage - 1));
  }
  if (transactionNextBtn) {
    transactionNextBtn.addEventListener('click', () => loadTransactions(currentTransactionPage + 1));
  }
}

/**
 * Handle login form submission
 */
async function handleLogin(event) {
  event.preventDefault();
  
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const rememberMe = document.getElementById('remember-me').checked;
  
  // Validate inputs
  if (!email || !password) {
    displayAlert('Please enter both email and password', 'error');
    return;
  }
  
  try {
    showLoading();
    
    // IMPORTANT: Clear any existing session before logging in to ensure fresh token
    await clearSession();
    if (typeof chrome !== 'undefined' && chrome.storage) {
      await chrome.storage.local.clear();
      console.log('[Login] Cleared all storage before login');
    }
    
    // Call auth API
    const response = await apiClient.auth(email, password);
    
    hideLoading();
    
    if (response.success && response.token) {
      console.log('[Login] New token received:', response.token.substring(0, 50) + '...');
      console.log('[Login] Token contains =:', response.token.includes('='));
      console.log('[Login] Token contains /:', response.token.includes('/'));
      
      // Store session
      const session = {
        token: response.token,
        user_email: email,
        user_name: response.user_name || email,
        role: response.role || 'User',
        tenant: response.tenant || 'default',
        remember_me: rememberMe,
        expires_at: response.expires_at || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      };
      
      await storageManager.setSession(session);
      
      isLoggedIn = true;
      currentUser = session;
      
      displayAlert('Login successful!', 'success');
      
      // Clear form
      document.getElementById('login-form').reset();
      
      // Update admin tab visibility based on role
      if (typeof checkUserRole === 'function') {
        checkUserRole();
      }
      
      // Show logged-in view
      showLoggedInView();
    } else {
      displayAlert(response.message || 'Login failed. Please check your credentials.', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('Login error:', error);
    displayAlert('Login failed. Please try again.', 'error');
  }
}

/**
 * Handle logout
 */
async function handleLogout() {
  try {
    showLoading();
    
    // Call logout API if available (optional)
    // await apiClient.logout();
    
    // Clear session
    await clearSession();
    
    // Also clear from Chrome storage directly to ensure it's gone
    if (typeof chrome !== 'undefined' && chrome.storage) {
      await chrome.storage.local.remove('session');
      console.log('[Logout] Session cleared from Chrome storage');
    }
    
    hideLoading();
    
    isLoggedIn = false;
    currentUser = null;
    
    // Hide admin tab on logout
    if (typeof checkUserRole === 'function') {
      checkUserRole();
    }
    
    displayAlert('Logged out successfully. Please log in again to get a new session.', 'success');
    showLoggedOutView();
  } catch (error) {
    hideLoading();
    console.error('Logout error:', error);
    displayAlert('Logout failed. Session cleared locally.', 'warning');
    
    // Clear session anyway
    await clearSession();
    if (typeof chrome !== 'undefined' && chrome.storage) {
      await chrome.storage.local.remove('session');
    }
    isLoggedIn = false;
    currentUser = null;
    
    // Hide admin tab
    if (typeof checkUserRole === 'function') {
      checkUserRole();
    }
    
    showLoggedOutView();
  }
}

/**
 * Handle forget password link click
 */
function handleForgetPassword(event) {
  event.preventDefault();
  
  // Show forget password form (to be implemented in task 16.9)
  displayAlert('Password recovery feature will be implemented soon', 'info');
}

/**
 * Handle sign up link click
 */
function handleSignup(event) {
  event.preventDefault();
  
  // Show sign up form (to be implemented in task 16.10)
  displayAlert('User registration feature will be implemented soon', 'info');
}

/**
 * Show logged-out view
 */
function showLoggedOutView() {
  const loggedOutView = document.getElementById('profile-logged-out');
  const loggedInView = document.getElementById('profile-logged-in');
  
  if (loggedOutView) {
    loggedOutView.classList.remove('hidden');
  }
  
  if (loggedInView) {
    loggedInView.classList.add('hidden');
  }
}

/**
 * Show logged-in view
 */
function showLoggedInView() {
  const loggedOutView = document.getElementById('profile-logged-out');
  const loggedInView = document.getElementById('profile-logged-in');
  
  if (loggedOutView) {
    loggedOutView.classList.add('hidden');
  }
  
  if (loggedInView) {
    loggedInView.classList.remove('hidden');
  }
  
  // Load profile data
  loadProfile();
}

/**
 * Clear session from storage
 */
async function clearSession() {
  try {
    await storageManager.clearSession();
  } catch (error) {
    console.error('Error clearing session:', error);
  }
}

/**
 * Load profile data and statistics
 */
async function loadProfile() {
  try {
    // Update user name heading
    const userNameHeading = document.getElementById('user-name-heading');
    if (userNameHeading && currentUser) {
      userNameHeading.textContent = `Welcome, ${currentUser.user_name}`;
    }

    // Load documents processed count
    loadDocumentsProcessed();

    // Load available balance
    loadAvailableBalance();

    // Load profile fields
    loadProfileFields();

    // Load transaction history
    loadTransactions(1);
  } catch (error) {
    console.error('Error loading profile:', error);
    displayAlert('Failed to load profile data', 'error');
  }
}

/**
 * Load documents processed count
 */
async function loadDocumentsProcessed() {
  try {
    const response = await apiClient.getTotalDocumentProcessed();
    console.log("Hi" + response)
    
    const countElement = document.getElementById('documents-processed-count');
    if (countElement && response.success) {
      countElement.textContent = response.count || 0;
    }
  } catch (error) {
    console.error('Error loading documents processed:', error);
  }
}

/**
 * Load available balance
 */
async function loadAvailableBalance() {
  try {
    console.log('[Balance] Loading available balance...');
    const session = await storageManager.getSession();
    console.log('[Balance] Current session:', { email: session?.user_email, tenant: session?.tenant, hasToken: !!session?.token });
    
    const response = await apiClient.getAvailableBalance();
    console.log('[Balance] API response:', response);
    
    const balanceElement = document.getElementById('available-balance-amount');
    if (balanceElement) {
      if (response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
        console.log('[Balance] Balance updated to: $' + balance.toFixed(2));
      } else {
        console.error('[Balance] API returned success=false:', response);
        balanceElement.textContent = '$0.00';
      }
    } else {
      console.error('[Balance] Balance element not found');
    }
  } catch (error) {
    console.error('[Balance] Error loading available balance:', error);
    const balanceElement = document.getElementById('available-balance-amount');
    if (balanceElement) {
      balanceElement.textContent = '$0.00';
    }
  }
}


/**
 * Load profile fields (first name, last name)
 */
async function loadProfileFields() {
  try {
    // For now, parse from user_name if available
    // In a real implementation, this would come from a profile API
    if (currentUser && currentUser.user_name) {
      const nameParts = currentUser.user_name.split(' ');
      const firstNameInput = document.getElementById('profile-first-name');
      const lastNameInput = document.getElementById('profile-last-name');
      
      if (firstNameInput && nameParts.length > 0) {
        firstNameInput.value = nameParts[0];
      }
      
      if (lastNameInput && nameParts.length > 1) {
        lastNameInput.value = nameParts.slice(1).join(' ');
      }
    }
  } catch (error) {
    console.error('Error loading profile fields:', error);
  }
}

/**
 * Toggle profile settings section
 */
function toggleProfileSettings() {
  const content = document.getElementById('profile-settings-content');
  const icon = document.getElementById('profile-settings-icon');
  
  if (content && icon) {
    content.classList.toggle('hidden');
    icon.textContent = content.classList.contains('hidden') ? '▼' : '▲';
  }
}

/**
 * Toggle change password section
 */
function toggleChangePassword() {
  const content = document.getElementById('change-password-content');
  const icon = document.getElementById('change-password-icon');
  
  if (content && icon) {
    content.classList.toggle('hidden');
    icon.textContent = content.classList.contains('hidden') ? '▼' : '▲';
  }
}

/**
 * Toggle transaction history section
 */
function toggleTransactionHistory() {
  const content = document.getElementById('transaction-history-content');
  const icon = document.getElementById('transaction-history-icon');
  
  if (content && icon) {
    content.classList.toggle('hidden');
    icon.textContent = content.classList.contains('hidden') ? '▼' : '▲';
  }
}

/**
 * Handle save profile
 */
async function handleSaveProfile() {
  const firstName = document.getElementById('profile-first-name').value.trim();
  const lastName = document.getElementById('profile-last-name').value.trim();
  
  if (!firstName || !lastName) {
    displayAlert('Please enter both first name and last name', 'error');
    return;
  }
  
  try {
    showLoading();
    
    const response = await apiClient.updateProfile(firstName, lastName);
    
    hideLoading();
    
    if (response.success) {
      // Update current user name
      currentUser.user_name = `${firstName} ${lastName}`;
      await storageManager.setSession(currentUser);
      
      // Update heading
      const userNameHeading = document.getElementById('user-name-heading');
      if (userNameHeading) {
        userNameHeading.textContent = `Welcome, ${currentUser.user_name}`;
      }
      
      displayAlert('Profile updated successfully', 'success');
    } else {
      displayAlert(response.message || 'Failed to update profile', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('Error saving profile:', error);
    displayAlert('Failed to update profile', 'error');
  }
}

/**
 * Handle change password
 */
async function handleChangePassword() {
  const currentPassword = document.getElementById('current-password').value;
  const newPassword = document.getElementById('new-password').value;
  const confirmPassword = document.getElementById('confirm-password').value;
  
  // Validate inputs
  if (!currentPassword || !newPassword || !confirmPassword) {
    displayAlert('Please fill in all password fields', 'error');
    return;
  }
  
  if (newPassword !== confirmPassword) {
    displayAlert('New password and confirm password do not match', 'error');
    return;
  }
  
  if (newPassword.length < 8) {
    displayAlert('New password must be at least 8 characters long', 'error');
    return;
  }
  
  try {
    showLoading();
    
    const response = await apiClient.changePassword(currentPassword, newPassword, confirmPassword);
    
    hideLoading();
    
    if (response.success) {
      // Clear password fields
      document.getElementById('current-password').value = '';
      document.getElementById('new-password').value = '';
      document.getElementById('confirm-password').value = '';
      
      displayAlert('Password changed successfully', 'success');
    } else {
      displayAlert(response.message || 'Failed to change password', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('Error changing password:', error);
    displayAlert('Failed to change password', 'error');
  }
}

/**
 * Load transaction history with pagination
 */
async function loadTransactions(page = 1) {
  try {
    showLoading();
    
    const response = await apiClient.getMyTransactions(page, 20);
    
    hideLoading();
    
    if (response.success && response.transactions) {
      currentTransactionPage = page;
      totalTransactionPages = response.total_pages || 1;
      
      displayTransactions(response.transactions);
      updateTransactionPagination();
    } else {
      displayAlert('Failed to load transaction history', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('Error loading transactions:', error);
    displayAlert('Failed to load transaction history', 'error');
  }
}

/**
 * Display transactions in table
 */
function displayTransactions(transactions) {
  const tbody = document.getElementById('transaction-history-body');
  
  if (!tbody) return;
  
  // Clear existing rows
  tbody.innerHTML = '';
  
  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="border border-gray-300 px-4 py-8 text-center text-gray-500">
          No transactions available
        </td>
      </tr>
    `;
    return;
  }
  
  // Add transaction rows
  transactions.forEach(transaction => {
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-50';
    
    const timestamp = new Date(transaction.timestamp).toLocaleString();
    const processingId = transaction.processing_id || '-';
    const pages = transaction.pages || '-';
    const action = transaction.action || '-';
    const amount = transaction.amount ? `$${Math.abs(transaction.amount).toFixed(2)}` : '$0.00';
    const remainingBalance = transaction.remaining_balance ? `$${transaction.remaining_balance.toFixed(2)}` : '$0.00';
    
    // Color code amount based on action
    const amountClass = transaction.action === 'Utilized' ? 'text-red-600' : 'text-green-600';
    const amountPrefix = transaction.action === 'Utilized' ? '-' : '+';
    
    row.innerHTML = `
      <td class="border border-gray-300 px-4 py-2">${timestamp}</td>
      <td class="border border-gray-300 px-4 py-2">${processingId}</td>
      <td class="border border-gray-300 px-4 py-2">${pages}</td>
      <td class="border border-gray-300 px-4 py-2">${action}</td>
      <td class="border border-gray-300 px-4 py-2 text-right ${amountClass}">${amountPrefix}${amount}</td>
      <td class="border border-gray-300 px-4 py-2 text-right font-semibold">${remainingBalance}</td>
    `;
    
    tbody.appendChild(row);
  });
}

/**
 * Update transaction pagination controls
 */
function updateTransactionPagination() {
  const pageInfo = document.getElementById('transaction-page-info');
  const prevBtn = document.getElementById('transaction-prev-btn');
  const nextBtn = document.getElementById('transaction-next-btn');
  
  if (pageInfo) {
    pageInfo.textContent = `Page ${currentTransactionPage} of ${totalTransactionPages}`;
  }
  
  if (prevBtn) {
    prevBtn.disabled = currentTransactionPage <= 1;
    prevBtn.classList.toggle('opacity-50', currentTransactionPage <= 1);
    prevBtn.classList.toggle('cursor-not-allowed', currentTransactionPage <= 1);
  }
  
  if (nextBtn) {
    nextBtn.disabled = currentTransactionPage >= totalTransactionPages;
    nextBtn.classList.toggle('opacity-50', currentTransactionPage >= totalTransactionPages);
    nextBtn.classList.toggle('cursor-not-allowed', currentTransactionPage >= totalTransactionPages);
  }
}

/**
 * Handle top-up button click
 */
function handleTopup() {
  // This will be implemented in task 16.8
  displayAlert('Top-up feature will be implemented soon', 'info');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initProfile);
} else {
  initProfile();
}

