/**
 * Settings Tab Module
 * Handles FTP, Email, and API configuration management
 */

// Initialize settings when the tab is loaded
function initializeSettings() {
  loadSettings();
  attachEventListeners();
}

/**
 * Load settings from Local Storage
 * Retrieves all settings and decrypts passwords automatically
 * Requirements: 5.1, 5.3, 5.11, 13.2
 */
async function loadSettings() {
  try {
    // Use StorageManager to get all settings with automatic decryption
    const settings = await storageManager.getAllSettings();
    
    // Load FTP settings
    if (settings.ftp) {
      document.getElementById('ftp-host').value = settings.ftp.host || '';
      document.getElementById('ftp-port').value = settings.ftp.port || 21;
      document.getElementById('ftp-username').value = settings.ftp.username || '';
      // Password is automatically decrypted by StorageManager
      document.getElementById('ftp-password').value = settings.ftp.password || '';
      document.getElementById('ftp-remote-directory').value = settings.ftp.remote_directory || '';
    }
    
    // Load Email settings
    if (settings.email) {
      const mode = settings.email.mode || 'default';
      document.getElementById(`email-mode-${mode}`).checked = true;
      document.getElementById('email-to').value = settings.email.to || '';
      document.getElementById('email-cc').value = settings.email.cc || '';
      document.getElementById('email-subject').value = settings.email.subject || '';
      
      // Load attachment formats
      document.getElementById('email-format-csv').checked = settings.email.attachment_formats?.includes('csv') ?? true;
      document.getElementById('email-format-xlsx').checked = settings.email.attachment_formats?.includes('xlsx') ?? false;
      document.getElementById('email-format-json').checked = settings.email.attachment_formats?.includes('json') ?? false;
      
      // Load SMTP settings
      if (settings.email.smtp_server) {
        document.getElementById('smtp-server').value = settings.email.smtp_server || '';
        document.getElementById('smtp-port').value = settings.email.smtp_port || 587;
        document.getElementById('smtp-username').value = settings.email.smtp_username || '';
        // SMTP password is automatically decrypted by StorageManager
        document.getElementById('smtp-password').value = settings.email.smtp_password || '';
        document.getElementById('email-from').value = settings.email.email_from || '';
      }
      
      // Show/hide SMTP fields based on mode
      toggleSMTPFields(mode);
    }
    
    // Load API settings
    if (settings.api) {
      document.getElementById('api-method').value = settings.api.method || 'POST';
      document.getElementById('api-endpoint').value = settings.api.endpoint || '';
      document.getElementById('api-headers').value = settings.api.headers ? JSON.stringify(settings.api.headers, null, 2) : '';
      document.getElementById('api-body').value = settings.api.body || '';
    }
  } catch (error) {
    console.error('Error loading settings:', error);
    displayAlert('Failed to load settings', 'error');
  }
}

/**
 * Save settings to Local Storage
 * Encrypts passwords before storage automatically
 * Requirements: 5.1, 5.3, 5.11, 13.2
 */
async function saveSettings() {
  try {
    showLoading();
    
    // Collect FTP settings
    const ftpSettings = {
      host: document.getElementById('ftp-host').value,
      port: parseInt(document.getElementById('ftp-port').value) || 21,
      username: document.getElementById('ftp-username').value,
      password: document.getElementById('ftp-password').value,
      remote_directory: document.getElementById('ftp-remote-directory').value
    };
    
    // Collect Email settings
    const emailMode = document.querySelector('input[name="email-mode"]:checked').value;
    const attachmentFormats = [];
    if (document.getElementById('email-format-csv').checked) attachmentFormats.push('csv');
    if (document.getElementById('email-format-xlsx').checked) attachmentFormats.push('xlsx');
    if (document.getElementById('email-format-json').checked) attachmentFormats.push('json');
    
    const emailSettings = {
      mode: emailMode,
      to: document.getElementById('email-to').value,
      cc: document.getElementById('email-cc').value,
      subject: document.getElementById('email-subject').value,
      attachment_formats: attachmentFormats
    };
    
    // Add SMTP settings if SMTP mode is selected
    if (emailMode === 'smtp') {
      emailSettings.smtp_server = document.getElementById('smtp-server').value;
      emailSettings.smtp_port = parseInt(document.getElementById('smtp-port').value) || 587;
      emailSettings.smtp_username = document.getElementById('smtp-username').value;
      emailSettings.smtp_password = document.getElementById('smtp-password').value;
      emailSettings.email_from = document.getElementById('email-from').value;
    }
    
    // Collect API settings
    let apiHeaders = {};
    try {
      const headersText = document.getElementById('api-headers').value.trim();
      if (headersText) {
        apiHeaders = JSON.parse(headersText);
      }
    } catch (error) {
      hideLoading();
      showAlert('error', 'Invalid JSON format in API Headers');
      return;
    }
    
    const apiSettings = {
      method: document.getElementById('api-method').value,
      endpoint: document.getElementById('api-endpoint').value,
      headers: apiHeaders,
      body: document.getElementById('api-body').value
    };
    
    // Save settings using StorageManager with automatic encryption
    // FTP password will be encrypted automatically
    await storageManager.setFTPSettings(ftpSettings);
    
    // Email SMTP password will be encrypted automatically
    await storageManager.setEmailSettings(emailSettings);
    
    // API settings (no sensitive data to encrypt)
    await storageManager.setAPISettings(apiSettings);
    
    hideLoading();
    displayAlert('Settings saved successfully', 'success');
  } catch (error) {
    hideLoading();
    console.error('Error saving settings:', error);
    displayAlert('Failed to save settings: ' + error.message, 'error');
  }
}

/**
 * Test FTP connection
 */
async function testFTPConnection() {
  try {
    showLoading();
    
    const ftpConfig = {
      host: document.getElementById('ftp-host').value,
      port: parseInt(document.getElementById('ftp-port').value) || 21,
      username: document.getElementById('ftp-username').value,
      password: document.getElementById('ftp-password').value,
      remote_directory: document.getElementById('ftp-remote-directory').value
    };
    
    // Validate required fields
    if (!ftpConfig.host || !ftpConfig.username || !ftpConfig.password) {
      hideLoading();
      displayAlert('Please fill in all required FTP fields', 'error');
      return;
    }
    
    // Call FTP test API
    const response = await apiCall('/ftp', 'POST', {
      config: ftpConfig,
      test: true
    });
    
    hideLoading();
    
    if (response.success) {
      displayAlert('FTP connection successful', 'success');
    } else {
      displayAlert(response.message || 'FTP connection failed', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('FTP test error:', error);
    displayAlert('FTP connection test failed: ' + error.message, 'error');
  }
}

/**
 * Test Email connection
 */
async function testEmailConnection() {
  try {
    showLoading();
    
    const emailMode = document.querySelector('input[name="email-mode"]:checked').value;
    const emailTo = document.getElementById('email-to').value;
    
    if (!emailTo) {
      hideLoading();
      displayAlert('Please enter an email address', 'error');
      return;
    }
    
    if (emailMode === 'default') {
      // Test using default server API
      const response = await apiCall('/send_email', 'POST', {
        to: emailTo,
        subject: 'Test Email',
        body: 'This is a test email from AI Document Processing Extension',
        test: true
      });
      
      hideLoading();
      
      if (response.success) {
        displayAlert('Email sent successfully via default server', 'success');
      } else {
        displayAlert(response.message || 'Email sending failed', 'error');
      }
    } else {
      // Test using SMTP
      const smtpConfig = {
        server: document.getElementById('smtp-server').value,
        port: parseInt(document.getElementById('smtp-port').value) || 587,
        username: document.getElementById('smtp-username').value,
        password: document.getElementById('smtp-password').value,
        from: document.getElementById('email-from').value
      };
      
      // Validate required fields
      if (!smtpConfig.server || !smtpConfig.username || !smtpConfig.password || !smtpConfig.from) {
        hideLoading();
        displayAlert('Please fill in all required SMTP fields', 'error');
        return;
      }
      
      // TODO: Implement SMTP.js client-side testing
      // For now, just validate the configuration
      hideLoading();
      displayAlert('SMTP configuration validated. Full testing will be implemented with smtp.js library', 'info');
    }
  } catch (error) {
    hideLoading();
    console.error('Email test error:', error);
    displayAlert('Email connection test failed: ' + error.message, 'error');
  }
}

/**
 * Test API connection
 */
async function testAPIConnection() {
  try {
    showLoading();
    
    const endpoint = document.getElementById('api-endpoint').value;
    const method = document.getElementById('api-method').value;
    
    if (!endpoint) {
      hideLoading();
      displayAlert('Please enter an API endpoint', 'error');
      return;
    }
    
    // Parse headers
    let headers = {};
    try {
      const headersText = document.getElementById('api-headers').value.trim();
      if (headersText) {
        headers = JSON.parse(headersText);
      }
    } catch (error) {
      hideLoading();
      displayAlert('Invalid JSON format in API Headers', 'error');
      return;
    }
    
    // Send test request
    const testData = { test: true, message: 'Test request from AI Document Processing Extension' };
    
    const response = await fetch(endpoint, {
      method: method,
      headers: headers,
      body: method === 'POST' ? JSON.stringify(testData) : undefined
    });
    
    hideLoading();
    
    if (response.ok) {
      displayAlert(`API connection successful (Status: ${response.status})`, 'success');
    } else {
      displayAlert(`API connection failed (Status: ${response.status})`, 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('API test error:', error);
    displayAlert('API connection test failed: ' + error.message, 'error');
  }
}

/**
 * Toggle SMTP fields visibility based on email mode
 */
function toggleSMTPFields(mode) {
  const smtpFields = document.getElementById('smtp-fields');
  if (mode === 'smtp') {
    smtpFields.classList.remove('hidden');
  } else {
    smtpFields.classList.add('hidden');
  }
}

/**
 * Attach event listeners
 */
function attachEventListeners() {
  // Email mode radio buttons
  document.querySelectorAll('input[name="email-mode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      toggleSMTPFields(e.target.value);
    });
  });
  
  // Test connection buttons
  document.getElementById('test-ftp-btn').addEventListener('click', testFTPConnection);
  document.getElementById('test-email-btn').addEventListener('click', testEmailConnection);
  document.getElementById('test-api-btn').addEventListener('click', testAPIConnection);
  
  // Save button
  document.getElementById('save-settings-btn').addEventListener('click', saveSettings);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeSettings);
} else {
  initializeSettings();
}

