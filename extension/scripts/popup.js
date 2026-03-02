/**
 * Main Popup Script
 * Handles tab navigation and initializes the extension UI
 */

// Tab navigation
document.addEventListener('DOMContentLoaded', () => {
  console.log('AI Document Processing Extension loaded');

  // Initialize tab navigation
  initTabNavigation();
  
  // Initialize dashboard
  if (typeof initDashboard === 'function') {
    initDashboard();
  }
  
  // Initialize prompts
  if (typeof initPrompts === 'function') {
    initPrompts();
  }
  
  // Initialize settings
  if (typeof initSettings === 'function') {
    initSettings();
  }
  
  // Initialize profile
  if (typeof initProfile === 'function') {
    initProfile();
  }
  
  // Initialize admin
  if (typeof initAdmin === 'function') {
    initAdmin();
  }
  
  // Check if user is logged in and show/hide admin tab
  checkUserRole();
  
  // Load initial data
  loadInitialData();
});

/**
 * Initialize tab navigation
 */
function initTabNavigation() {
  const tabItems = document.querySelectorAll('.tab-item');
  const tabContents = document.querySelectorAll('.tab-content');

  tabItems.forEach(item => {
    item.addEventListener('click', () => {
      const tabName = item.getAttribute('data-tab');
      console.log('[Popup] Tab clicked:', tabName);
      
      // Remove active class from all tabs
      tabItems.forEach(t => {
        t.classList.remove('active');
      });
      
      // Hide all tab contents
      tabContents.forEach(content => {
        content.classList.add('hidden');
      });
      
      // Activate clicked tab
      item.classList.add('active');
      
      // Show corresponding content
      const targetContent = document.getElementById(`${tabName}-tab`);
      if (targetContent) {
        targetContent.classList.remove('hidden');
        console.log('[Popup] Tab content shown:', tabName);
      } else {
        console.error('[Popup] Tab content not found:', `${tabName}-tab`);
      }
      
      // Load data when specific tabs become visible
      if (tabName === 'prompts') {
        console.log('[Popup] Prompts tab detected, calling onPromptsTabVisible()');
        if (typeof window.onPromptsTabVisible === 'function') {
          window.onPromptsTabVisible();
        } else {
          console.error('[Popup] window.onPromptsTabVisible is not a function!');
        }
      } else if (tabName === 'dashboard') {
        console.log('[Popup] Dashboard tab detected, calling onDashboardTabVisible()');
        if (typeof window.onDashboardTabVisible === 'function') {
          window.onDashboardTabVisible();
        } else {
          console.error('[Popup] window.onDashboardTabVisible is not a function!');
        }
      } else if (tabName === 'profile') {
        console.log('[Popup] Profile tab detected, calling onProfileTabVisible()');
        if (typeof window.onProfileTabVisible === 'function') {
          window.onProfileTabVisible();
        } else {
          console.error('[Popup] window.onProfileTabVisible is not a function!');
        }
      }
    });
  });

  // Activate first tab by default
  if (tabItems.length > 0) {
    tabItems[0].click();
  }
}

/**
 * Check user role and show/hide admin tab
 */
async function checkUserRole() {
  try {
    // Import storage manager
    const session = await storageManager.getSession();
    
    const adminTabNav = document.getElementById('admin-tab-nav');
    
    if (session && (session.role === 'System User' || session.role === 'System_User')) {
      // Show admin tab for System Users
      if (adminTabNav) {
        adminTabNav.classList.remove('hidden');
      }
    } else {
      // Hide admin tab for non-System Users
      if (adminTabNav) {
        adminTabNav.classList.add('hidden');
      }
    }
  } catch (error) {
    console.error('Error checking user role:', error);
    // Hide admin tab on error
    const adminTabNav = document.getElementById('admin-tab-nav');
    if (adminTabNav) {
      adminTabNav.classList.add('hidden');
    }
  }
}

/**
 * Load initial data
 */
async function loadInitialData() {
  try {
    // Load prompts for dropdown
    await loadPromptsForTab();
    
    // Note: loadHistory() is now called by initDashboard()
  } catch (error) {
    console.error('Error loading initial data:', error);
  }
}

/**
 * Load prompts from cache or API
 */
async function loadPromptsForTab() {
  try {
    const promptsData = await storageManager.getPrompts();
    
    if (promptsData && promptsData.prompts) {
      populatePromptDropdown(promptsData.prompts);
    } else {
      // TODO: Fetch from API when API client is implemented
      console.log('No cached prompts found');
    }
  } catch (error) {
    console.error('Error loading prompts:', error);
  }
}

/**
 * Populate prompt dropdown
 */
function populatePromptDropdown(prompts) {
  const promptSelect = document.getElementById('prompt-select');
  if (!promptSelect) return;
  
  // Clear existing options except the first one
  promptSelect.innerHTML = '<option value="">-- Select Document Type --</option>';
  
  prompts.forEach(prompt => {
    const option = document.createElement('option');
    option.value = prompt.prompt_id;
    option.textContent = prompt.prompt_name;
    promptSelect.appendChild(option);
  });
}

/**
 * Show loading indicator
 */
function showLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) {
    overlay.classList.remove('hidden');
  }
}

/**
 * Hide loading indicator
 */
function hideLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) {
    overlay.classList.add('hidden');
  }
}

/**
 * Display alert message
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, error, warning, info)
 */
function displayAlert(message, type = 'info') {
  const container = document.getElementById('alert-container');
  if (!container) return;
  
  const alert = document.createElement('div');
  alert.className = `px-4 py-3 rounded-lg shadow-lg ${getAlertClasses(type)} animate-slide-in`;
  alert.textContent = message;
  
  container.appendChild(alert);
  
  // Auto-dismiss success alerts after 3 seconds
  if (type === 'success') {
    setTimeout(() => {
      alert.remove();
    }, 3000);
  } else {
    // Add close button for other alerts
    const closeBtn = document.createElement('button');
    closeBtn.className = 'ml-4 font-bold';
    closeBtn.textContent = '×';
    closeBtn.onclick = () => alert.remove();
    alert.appendChild(closeBtn);
  }
}

/**
 * Get alert CSS classes based on type
 */
function getAlertClasses(type) {
  const classes = {
    success: 'bg-green-100 text-green-800 border border-green-300',
    error: 'bg-red-100 text-red-800 border border-red-300',
    warning: 'bg-yellow-100 text-yellow-800 border border-yellow-300',
    info: 'bg-blue-100 text-blue-800 border border-blue-300'
  };
  return classes[type] || classes.info;
}

/**
 * Toggle collapsible section
 */
function toggleCollapsible(toggleId, contentId, iconId) {
  const toggle = document.getElementById(toggleId);
  const content = document.getElementById(contentId);
  const icon = document.getElementById(iconId);
  
  if (!toggle || !content || !icon) return;
  
  toggle.addEventListener('click', () => {
    content.classList.toggle('hidden');
    icon.textContent = content.classList.contains('hidden') ? '▼' : '▲';
  });
}

// Initialize collapsible sections
document.addEventListener('DOMContentLoaded', () => {
  toggleCollapsible('metadata-toggle', 'metadata-content', 'metadata-icon');
  toggleCollapsible('history-toggle', 'history-content', 'history-icon');
});
