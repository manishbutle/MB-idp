/**
 * Alert System Integration Demo
 * This file demonstrates how to use the displayAlert function
 * in various scenarios throughout the extension
 */

// Example 1: Success alert after export
function handleExportSuccess(format) {
  displayAlert(`${format} file downloaded successfully!`, 'success');
}

// Example 2: Error alert on API failure
function handleApiError(operation, error) {
  displayAlert(`Failed to ${operation}: ${error.message}`, 'error');
}

// Example 3: Warning alert for validation
function handleValidationWarning(message) {
  displayAlert(message, 'warning');
}

// Example 4: Info alert for general messages
function handleInfoMessage(message) {
  displayAlert(message, 'info');
}

// Example usage in CSV export
function exportToCSV(data) {
  try {
    if (!data || Object.keys(data).length === 0) {
      displayAlert('No data available to export', 'warning');
      return;
    }
    
    // Export logic here...
    const csvData = convertToCSV(data);
    downloadFile(csvData, 'export.csv', 'text/csv');
    
    displayAlert('CSV file downloaded successfully!', 'success');
  } catch (error) {
    displayAlert(`Failed to export CSV: ${error.message}`, 'error');
  }
}

// Example usage in API calls
async function processDocument() {
  try {
    const response = await fetch('/api/process_document', {
      method: 'POST',
      body: JSON.stringify(documentData)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    displayAlert('Document processed successfully!', 'success');
    return result;
  } catch (error) {
    displayAlert(`Failed to process document: ${error.message}`, 'error');
    throw error;
  }
}

// Example usage in form validation
function validateForm(formData) {
  const errors = [];
  
  if (!formData.email) {
    errors.push('Email field is required');
  }
  
  if (!formData.password) {
    errors.push('Password field is required');
  }
  
  if (errors.length > 0) {
    displayAlert(`Validation failed: ${errors.join(', ')}`, 'error');
    return false;
  }
  
  return true;
}

// Example usage in settings save
function saveSettings(settings) {
  try {
    // Validate settings
    if (!settings.ftp.host) {
      displayAlert('FTP host is required', 'warning');
      return;
    }
    
    // Save to storage
    localStorage.setItem('settings', JSON.stringify(settings));
    displayAlert('Settings saved successfully!', 'success');
  } catch (error) {
    displayAlert(`Failed to save settings: ${error.message}`, 'error');
  }
}

// Example usage in connection testing
async function testConnection(type, config) {
  try {
    displayAlert(`Testing ${type} connection...`, 'info');
    
    const response = await fetch(`/api/test_${type}`, {
      method: 'POST',
      body: JSON.stringify(config)
    });
    
    if (response.ok) {
      displayAlert(`${type} connection successful!`, 'success');
    } else {
      displayAlert(`${type} connection failed: ${response.statusText}`, 'error');
    }
  } catch (error) {
    displayAlert(`${type} connection error: ${error.message}`, 'error');
  }
}

// Helper functions (placeholders)
function convertToCSV(data) {
  // CSV conversion logic
  return 'csv data';
}

function downloadFile(content, filename, mimeType) {
  // File download logic
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
