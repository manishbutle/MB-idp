/**
 * Dashboard Tab Module
 * Handles document processing workflow and result display
 * Requirements: 1.1, 1.12, 15.2, 15.3, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10, 2.11
 */

// State management for dashboard
const dashboardState = {
  currentResults: null,
  currentMetadata: null,
  historyPage: 1,
  historyLimit: 20
};

/**
 * Initialize dashboard functionality
 */
function initDashboard() {
  // Process Document button
  const processBtn = document.getElementById('process-document-btn');
  if (processBtn) {
    processBtn.addEventListener('click', handleProcessDocument);
  }

  // Copy to Clipboard button
  const copyClipboardBtn = document.getElementById('copy-clipboard-btn');
  if (copyClipboardBtn) {
    copyClipboardBtn.addEventListener('click', handleCopyToClipboard);
  }

  // Export to CSV button
  const exportCsvBtn = document.getElementById('export-csv-btn');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', handleExportToCSV);
  }

  // Export to XLSX button
  const exportXlsxBtn = document.getElementById('export-xlsx-btn');
  if (exportXlsxBtn) {
    exportXlsxBtn.addEventListener('click', handleExportToXLSX);
  }

  // Export to JSON button
  const exportJsonBtn = document.getElementById('export-json-btn');
  if (exportJsonBtn) {
    exportJsonBtn.addEventListener('click', handleExportToJSON);
  }

  // Export to FTP button
  const exportFtpBtn = document.getElementById('export-ftp-btn');
  if (exportFtpBtn) {
    exportFtpBtn.addEventListener('click', handleExportToFTP);
  }

  // Submit to API button
  const submitApiBtn = document.getElementById('submit-api-btn');
  if (submitApiBtn) {
    submitApiBtn.addEventListener('click', handleSubmitToAPI);
  }

  // Send Email button
  const sendEmailBtn = document.getElementById('send-email-btn');
  if (sendEmailBtn) {
    sendEmailBtn.addEventListener('click', handleSendEmail);
  }

  // History Refresh button
  const historyRefreshBtn = document.getElementById('history-refresh-btn');
  console.log('[Dashboard] History refresh button:', historyRefreshBtn);
  if (historyRefreshBtn) {
    console.log('[Dashboard] Attaching click listener to history refresh button');
    historyRefreshBtn.addEventListener('click', async () => {
      console.log('[Dashboard] History refresh button clicked!');
      await loadHistory();
    });
  } else {
    console.error('[Dashboard] History refresh button not found!');
  }

  // Load history on initialization (if user is logged in)
  checkAndLoadHistory();
}

/**
 * Check if user is logged in and load history
 */
async function checkAndLoadHistory() {
  try {
    const session = await storageManager.getSession();
    if (session && session.token) {
      console.log('[Dashboard] User is logged in, loading history');
      await loadHistory();
    }
  } catch (error) {
    console.error('[Dashboard] Error checking session:', error);
  }
}

/**
 * Callback when Dashboard tab becomes visible
 * Called by popup.js when user switches to Dashboard tab
 */
window.onDashboardTabVisible = async function() {
  console.log('[Dashboard] Tab became visible, loading history');
  try {
    const session = await storageManager.getSession();
    if (session && session.token) {
      await loadHistory();
    } else {
      console.log('[Dashboard] User not logged in, skipping history load');
    }
  } catch (error) {
    console.error('[Dashboard] Error loading history on tab visible:', error);
  }
};

/**
 * Handle process document button click
 * Shows confirmation dialog before processing
 * Requirements: 1.1, 1.12
 */
async function handleProcessDocument() {
  try {
    // Show confirmation dialog (Requirement 1.12)
    const confirmed = await showConfirmationDialog(
      'Process Document',
      'Are you sure you want to process the current document? This will use credits from your account.'
    );

    if (!confirmed) {
      return; // User clicked "No"
    }

    // Get current tab's document
    const documentData = await getCurrentDocument();
    
    if (!documentData) {
      displayAlert('No document found in current tab', 'error');
      return;
    }

    // Process the document
    await processDocument(documentData);
  } catch (error) {
    console.error('Error handling process document:', error);
    displayAlert(error.message || 'Failed to process document', 'error');
  }
}

/**
 * Show confirmation dialog with Yes/No options
 * Requirements: 1.12
 * @param {string} title - Dialog title
 * @param {string} message - Dialog message
 * @returns {Promise<boolean>} True if user clicked Yes, false otherwise
 */
function showConfirmationDialog(title, message) {
  return new Promise((resolve) => {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    overlay.id = 'confirmation-dialog';

    // Create dialog
    const dialog = document.createElement('div');
    dialog.className = 'bg-white rounded-lg p-6 max-w-md mx-4 shadow-xl';
    dialog.innerHTML = `
      <h3 class="text-lg font-semibold mb-3 text-gray-800">${title}</h3>
      <p class="text-gray-600 mb-6">${message}</p>
      <div class="flex justify-end gap-3">
        <button id="confirm-no-btn" class="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-800 rounded-lg transition-colors">
          No
        </button>
        <button id="confirm-yes-btn" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
          Yes
        </button>
      </div>
    `;

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Handle button clicks
    document.getElementById('confirm-yes-btn').addEventListener('click', () => {
      overlay.remove();
      resolve(true);
    });

    document.getElementById('confirm-no-btn').addEventListener('click', () => {
      overlay.remove();
      resolve(false);
    });

    // Handle click outside dialog
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.remove();
        resolve(false);
      }
    });
  });
}

/**
 * Get current document from active tab
 * @returns {Promise<Object>} Document data
 */
async function getCurrentDocument() {
  try {
    // Get user session
    const session = await storageManager.getSession();
    console.log('[Dashboard] Session data:', session);
    
    if (!session) {
      throw new Error('User not logged in. Please log in first.');
    }
    
    // Extract user email and tenant from session
    // Session might have different property names
    const userEmail = session.email || session.user_email || session.userEmail;
    const tenant = session.tenant || session.tenant_id || session.tenantId;
    
    console.log('[Dashboard] User email:', userEmail);
    console.log('[Dashboard] Tenant:', tenant);
    
    if (!userEmail || !tenant) {
      throw new Error('User session is incomplete. Please log in again.');
    }
    
    // Get selected prompt
    const promptSelect = document.getElementById('prompt-select');
    const selectedPromptId = promptSelect ? promptSelect.value : '';
    
    if (!selectedPromptId) {
      throw new Error('Please select a document type/prompt');
    }

    // Get active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab) {
      throw new Error('No active tab found');
    }

    // Check if the current tab is a PDF or image
    const url = tab.url || '';
    const isPdf = url.endsWith('.pdf') || url.includes('.pdf?') || url.includes('application/pdf');
    const isImage = /\.(jpg|jpeg|png|gif|webp)(\?|$)/i.test(url) || 
                    url.includes('image/jpeg') || 
                    url.includes('image/png') || 
                    url.includes('image/gif') || 
                    url.includes('image/webp');
    
    let documentData = null;
    let documentName = tab.title || 'document';
    let fileType = 'pdf';
    let fileSize = 0; // Initialize fileSize at function scope
    
    if (isPdf || isImage) {
      // Determine file type
      if (isImage) {
        if (url.match(/\.jpe?g/i) || url.includes('image/jpeg')) {
          fileType = 'jpeg';
          documentName = documentName.endsWith('.jpg') || documentName.endsWith('.jpeg') ? documentName : documentName + '.jpg';
        } else if (url.match(/\.png/i) || url.includes('image/png')) {
          fileType = 'png';
          documentName = documentName.endsWith('.png') ? documentName : documentName + '.png';
        } else if (url.match(/\.gif/i) || url.includes('image/gif')) {
          fileType = 'gif';
          documentName = documentName.endsWith('.gif') ? documentName : documentName + '.gif';
        } else if (url.match(/\.webp/i) || url.includes('image/webp')) {
          fileType = 'webp';
          documentName = documentName.endsWith('.webp') ? documentName : documentName + '.webp';
        }
      } else {
        fileType = 'pdf';
        documentName = documentName.endsWith('.pdf') ? documentName : documentName + '.pdf';
      }
      
      // Fetch document from URL
      try {
        console.log('[Dashboard] Fetching document from URL:', url);
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch document: ${response.status} ${response.statusText}`);
        }
        
        // Get document as ArrayBuffer
        const arrayBuffer = await response.arrayBuffer();
        const fileSize = arrayBuffer.byteLength;
        
        // Convert to base64
        const bytes = new Uint8Array(arrayBuffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        documentData = btoa(binary);
        
        console.log('[Dashboard] Document fetched successfully, type:', fileType, 'size:', fileSize, 'bytes');
      } catch (error) {
        console.error('[Dashboard] Error fetching document:', error);
        throw new Error('Failed to fetch document from current tab. Please ensure the document is accessible.');
      }
    } else {
      // Not a supported document type
      throw new Error('Please open a PDF or image file (JPG, PNG, GIF, WEBP) in the current tab.');
    }
    
    return {
      user_email: userEmail,
      tenant: tenant,
      document_name: documentName,
      document_data: documentData,
      prompt_id: selectedPromptId,
      url: tab.url,
      file_type: fileType,
      file_size: fileSize
    };
  } catch (error) {
    console.error('Error getting current document:', error);
    throw error;
  }
}

/**
 * Process document by sending to API
 * Requirements: 1.1, 15.2, 15.3
 * @param {Object} documentData - Document data to process
 */
async function processDocument(documentData) {
  try {
    // Show loading indicator (Requirement 15.2)
    showLoading();

    // Send document to API (Requirement 1.1)
    const response = await apiClient.processDocument(documentData);

    // Hide loading indicator (Requirement 15.3)
    hideLoading();

    // Handle successful response
    if (response && response.success) {
      // Display results
      displayResults(response.results);
      
      // Display metadata
      displayMetadata(response.metadata);
      
      // Update document type in prompt selection
      if (response.document_type) {
        updatePromptSelection(response.document_type);
      }

      // Refresh history
      await loadHistory();

      // Show success message
      displayAlert('Document processed successfully!', 'success');
    } else {
      throw new Error('Invalid response from server');
    }
  } catch (error) {
    hideLoading();
    console.error('Error processing document:', error);
    
    // Display error alert
    displayAlert(
      error.message || 'Failed to process document. Please try again.',
      'error'
    );
  }
}

/**
 * Display extraction results in RESULT table
 * Requirements: 2.2, 2.3, 2.4, 2.11
 * @param {Object|Array} results - Extraction results (field-value pairs or array of transactions)
 */
function displayResults(results) {
  const resultSection = document.getElementById('result-section');
  const resultTableBody = document.getElementById('result-table-body');
  const actionSection = document.getElementById('action-section');

  if (!resultSection || !resultTableBody) return;

  // Validate results
  if (!results) {
    console.error('Invalid results data:', results);
    displayAlert('Invalid results data received', 'error');
    return;
  }

  // Check if results contain multiple transactions
  let transactionsArray = [];
  
  if (results.transactions && Array.isArray(results.transactions)) {
    // Multiple transactions
    transactionsArray = results.transactions;
  } else if (typeof results === 'object' && !Array.isArray(results)) {
    // Single transaction
    transactionsArray = [results];
  } else {
    console.error('Unexpected results format:', results);
    displayAlert('Unexpected results format received', 'error');
    return;
  }

  // Store results in state (deep copy to prevent external mutations)
  dashboardState.currentResults = JSON.parse(JSON.stringify(transactionsArray));

  // Clear existing rows
  resultTableBody.innerHTML = '';

  // Display each transaction
  transactionsArray.forEach((transaction, transactionIndex) => {
    // Add transaction header if multiple transactions
    if (transactionsArray.length > 1) {
      const headerRow = document.createElement('tr');
      headerRow.className = 'bg-blue-50';
      const headerCell = document.createElement('td');
      headerCell.colSpan = 2;
      headerCell.className = 'border border-gray-300 px-4 py-2 font-bold text-blue-800';
      headerCell.textContent = `Transaction ${transactionIndex + 1}`;
      headerRow.appendChild(headerCell);
      resultTableBody.appendChild(headerRow);
    }

    // Populate table with transaction fields (Requirement 2.4)
    Object.entries(transaction).forEach(([fieldName, value]) => {
      const row = document.createElement('tr');
      
      // Create field name cell
      const fieldCell = document.createElement('td');
      fieldCell.className = 'border border-gray-300 px-4 py-2 font-medium';
      fieldCell.textContent = fieldName; // Safe text content
      
      // Create value cell with editable input (Requirement 2.3)
      const valueCell = document.createElement('td');
      valueCell.className = 'border border-gray-300 px-4 py-2';
      
      const input = document.createElement('input');
      input.type = 'text';
      input.value = value || '';
      input.setAttribute('data-transaction-index', transactionIndex);
      input.setAttribute('data-field', fieldName);
      input.className = 'w-full px-2 py-1 border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 result-value-input';
      
      // Add event listener for inline editing (Requirement 2.11)
      input.addEventListener('change', (e) => {
        const txIndex = parseInt(e.target.getAttribute('data-transaction-index'));
        const field = e.target.getAttribute('data-field');
        const newValue = e.target.value;
        
        // Persist edited value in component state (Requirement 2.11)
        if (dashboardState.currentResults && dashboardState.currentResults[txIndex]) {
          dashboardState.currentResults[txIndex][field] = newValue;
        }
      });
      
      valueCell.appendChild(input);
      row.appendChild(fieldCell);
      row.appendChild(valueCell);
      resultTableBody.appendChild(row);
    });

    // Add spacing between transactions
    if (transactionsArray.length > 1 && transactionIndex < transactionsArray.length - 1) {
      const spacerRow = document.createElement('tr');
      spacerRow.className = 'h-2';
      const spacerCell = document.createElement('td');
      spacerCell.colSpan = 2;
      spacerCell.className = 'border-0';
      spacerRow.appendChild(spacerCell);
      resultTableBody.appendChild(spacerRow);
    }
  });

  // Show result and action sections
  resultSection.classList.remove('hidden');
  if (actionSection) {
    actionSection.classList.remove('hidden');
  }
}

/**
 * Display metadata in METADATA section
 * Requirements: 2.5, 2.6
 * @param {Object} metadata - Processing metadata
 */
function displayMetadata(metadata) {
  const metadataSection = document.getElementById('metadata-section');
  const metadataTableBody = document.getElementById('metadata-table-body');

  if (!metadataSection || !metadataTableBody) {
    console.error('Metadata section or table body not found');
    return;
  }

  // Validate metadata is an object
  if (!metadata || typeof metadata !== 'object') {
    console.error('Invalid metadata data:', metadata);
    displayAlert('Invalid metadata received', 'error');
    return;
  }

  // Store metadata in state (deep copy to prevent external mutations)
  dashboardState.currentMetadata = JSON.parse(JSON.stringify(metadata));

  // Clear existing rows
  metadataTableBody.innerHTML = '';

  // Define metadata fields to display (Requirement 2.6)
  // All required fields: Processing ID, Document Name, Prompt Name, Pages, 
  // Creation Date, File Type, File Size, Input Tokens, Output Tokens, LLM KPIs
  const metadataFields = [
    { key: 'processing_id', label: 'Processing ID' },
    { key: 'document_name', label: 'Document Name' },
    { key: 'prompt_name', label: 'Prompt Name' },
    { key: 'pages', label: 'Pages' },
    { key: 'creation_date', label: 'Creation Date' },
    { key: 'file_type', label: 'File Type' },
    { key: 'file_size', label: 'File Size' },
    { key: 'input_tokens', label: 'Input Tokens' },
    { key: 'output_tokens', label: 'Output Tokens' },
    { key: 'llm_kpis', label: 'LLM KPIs' }
  ];

  // Populate metadata table (Requirement 2.5)
  metadataFields.forEach(({ key, label }) => {
    let value = metadata[key];
    
    // Format values for better display
    if (value === null || value === undefined) {
      value = 'N/A';
    } else if (key === 'file_size') {
      // Format file size in human-readable format
      value = formatFileSize(value);
    } else if (key === 'creation_date') {
      // Format date if it's a timestamp
      value = formatDate(value);
    } else if (key === 'llm_kpis' && typeof value === 'object') {
      // Format LLM KPIs object as readable string
      value = formatLLMKPIs(value);
    }
    
    const row = document.createElement('tr');
    
    // Create label cell
    const labelCell = document.createElement('td');
    labelCell.className = 'border border-gray-300 px-4 py-2 font-medium bg-gray-50';
    labelCell.textContent = label; // Safe text content
    
    // Create value cell
    const valueCell = document.createElement('td');
    valueCell.className = 'border border-gray-300 px-4 py-2';
    valueCell.textContent = String(value); // Safe text content
    
    row.appendChild(labelCell);
    row.appendChild(valueCell);
    metadataTableBody.appendChild(row);
  });

  // Show metadata section (Requirement 2.5)
  metadataSection.classList.remove('hidden');
  
  // Initialize collapsible functionality if not already initialized
  initializeMetadataCollapsible();
}

/**
 * Initialize collapsible functionality for metadata section
 * Requirements: 2.5
 */
function initializeMetadataCollapsible() {
  const toggle = document.getElementById('metadata-toggle');
  const content = document.getElementById('metadata-content');
  const icon = document.getElementById('metadata-icon');
  
  if (!toggle || !content || !icon) {
    console.error('Metadata collapsible elements not found');
    return;
  }
  
  // Remove existing listener if any (to prevent duplicates)
  const newToggle = toggle.cloneNode(true);
  toggle.parentNode.replaceChild(newToggle, toggle);
  
  // Add click listener for collapsible functionality
  newToggle.addEventListener('click', () => {
    const isHidden = content.classList.contains('hidden');
    
    if (isHidden) {
      content.classList.remove('hidden');
      icon.textContent = '▲';
    } else {
      content.classList.add('hidden');
      icon.textContent = '▼';
    }
  });
}

/**
 * Format file size in human-readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size
 */
function formatFileSize(bytes) {
  if (typeof bytes !== 'number' || isNaN(bytes)) {
    return 'N/A';
  }
  
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format date in readable format
 * @param {string|number} date - Date string or timestamp
 * @returns {string} Formatted date
 */
function formatDate(date) {
  if (!date) return 'N/A';
  
  try {
    const dateObj = new Date(date);
    if (isNaN(dateObj.getTime())) {
      return String(date);
    }
    
    // Format as: YYYY-MM-DD HH:MM:SS
    return dateObj.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch (error) {
    console.error('Error formatting date:', error);
    return String(date);
  }
}

/**
 * Format LLM KPIs object as readable string
 * @param {Object} kpis - LLM KPIs object
 * @returns {string} Formatted KPIs string
 */
function formatLLMKPIs(kpis) {
  if (!kpis || typeof kpis !== 'object') {
    return 'N/A';
  }
  
  try {
    // Convert object to readable key-value pairs
    const entries = Object.entries(kpis)
      .map(([key, value]) => `${key}: ${value}`)
      .join(', ');
    
    return entries || 'N/A';
  } catch (error) {
    console.error('Error formatting LLM KPIs:', error);
    return 'N/A';
  }
}

/**
 * Update prompt selection dropdown with identified document type
 * Requirements: 2.2
 * @param {string} documentType - Identified document type
 */
function updatePromptSelection(documentType) {
  const promptSelect = document.getElementById('prompt-select');
  if (!promptSelect) return;

  // Find and select the matching option
  const options = promptSelect.options;
  for (let i = 0; i < options.length; i++) {
    if (options[i].textContent === documentType) {
      promptSelect.selectedIndex = i;
      break;
    }
  }
}

/**
 * Load processing history
 * Requirements: 2.8, 2.9, 2.10
 */
async function loadHistory() {
  try {
    console.log('[Dashboard] loadHistory called');
    const historyTableBody = document.getElementById('history-table-body');
    const historyPageInfo = document.getElementById('history-page-info');
    const historyContent = document.getElementById('history-content');

    if (!historyTableBody) {
      console.error('[Dashboard] History table body not found');
      return;
    }

    // Show loading indicator in table
    historyTableBody.innerHTML = `
      <tr>
        <td colspan="5" class="border border-gray-300 px-4 py-2 text-center text-gray-500">
          Loading history...
        </td>
      </tr>
    `;

    // Ensure history content is visible
    if (historyContent && historyContent.classList.contains('hidden')) {
      historyContent.classList.remove('hidden');
      const historyIcon = document.getElementById('history-icon');
      if (historyIcon) {
        historyIcon.textContent = '▲';
      }
    }

    console.log('[Dashboard] Fetching history from API, page:', dashboardState.historyPage, 'limit:', dashboardState.historyLimit);
    
    // Fetch history from API
    const response = await apiClient.getHistory(
      dashboardState.historyPage,
      dashboardState.historyLimit
    );

    console.log('[Dashboard] History API response:', response);

    if (!response || !response.success) {
      console.log('[Dashboard] No history data available');
      historyTableBody.innerHTML = `
        <tr>
          <td colspan="5" class="border border-gray-300 px-4 py-2 text-center text-gray-500">
            Failed to load history
          </td>
        </tr>
      `;
      return;
    }

    // Clear existing rows
    historyTableBody.innerHTML = '';

    // Populate history table (Requirement 2.9)
    const historyRecords = response.records || [];
    
    console.log('[Dashboard] Processing', historyRecords.length, 'history records');
    
    if (historyRecords.length === 0) {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td colspan="5" class="border border-gray-300 px-4 py-2 text-center text-gray-500">
          No processing history found
        </td>
      `;
      historyTableBody.appendChild(row);
      return;
    }
    
    historyRecords.forEach((record, index) => {
      const row = document.createElement('tr');
      row.className = 'hover:bg-gray-50';
      
      // Get values: prioritize transactions array from extracted_values, then transactions key, then extracted_values
      let extractedValues = record.extracted_values || {};
      if (extractedValues.transactions && Array.isArray(extractedValues.transactions)) {
        extractedValues = extractedValues.transactions;
      } else if (record.transactions) {
        extractedValues = record.transactions;
      }
      
      const valuesJson = JSON.stringify(extractedValues);
      const valuesPreview = valuesJson.length > 50 ? valuesJson.substring(0, 50) + '...' : valuesJson;
      const valueId = `history-value-${index}`;

      row.innerHTML = `
        <td class="border border-gray-300 px-4 py-2">${record.timestamp || 'N/A'}</td>
        <td class="border border-gray-300 px-4 py-2">${record.processing_id || 'N/A'}</td>
        <td class="border border-gray-300 px-4 py-2">${record.document_name || 'N/A'}</td>
        <td class="border border-gray-300 px-4 py-2">${record.pages || 'N/A'}</td>
        <td class="border border-gray-300 px-4 py-2 text-sm">
          <span id="${valueId}-preview" class="cursor-pointer text-blue-600 hover:underline">${valuesPreview}</span>
          <span id="${valueId}-full" class="hidden">${valuesJson}</span>
        </td>
      `;
      historyTableBody.appendChild(row);
      
      // Add click listener to toggle full/preview
      const previewEl = document.getElementById(`${valueId}-preview`);
      const fullEl = document.getElementById(`${valueId}-full`);
      if (previewEl && fullEl && valuesJson.length > 50) {
        previewEl.addEventListener('click', () => {
          if (fullEl.classList.contains('hidden')) {
            previewEl.classList.add('hidden');
            fullEl.classList.remove('hidden');
          } else {
            fullEl.classList.add('hidden');
            previewEl.classList.remove('hidden');
          }
        });
        fullEl.addEventListener('click', () => {
          fullEl.classList.add('hidden');
          previewEl.classList.remove('hidden');
        });
        fullEl.classList.add('cursor-pointer', 'text-blue-600', 'hover:underline');
      }
    });

    console.log('[Dashboard] History table populated with', historyRecords.length, 'records');

    // Update pagination info
    if (historyPageInfo) {
      historyPageInfo.textContent = `Page ${dashboardState.historyPage}`;
    }

    // Setup pagination buttons
    const totalPages = response.total_pages || 1;
    setupHistoryPagination(totalPages);
  } catch (error) {
    console.error('Error loading history:', error);
    // Don't show error alert for history loading failures
    // as this is a background operation
  }
}

/**
 * Setup history pagination controls
 * @param {number} totalPages - Total number of pages
 */
function setupHistoryPagination(totalPages) {
  const prevBtn = document.getElementById('history-prev-btn');
  const nextBtn = document.getElementById('history-next-btn');

  if (!prevBtn || !nextBtn) return;

  // Remove existing listeners
  const newPrevBtn = prevBtn.cloneNode(true);
  const newNextBtn = nextBtn.cloneNode(true);
  prevBtn.parentNode.replaceChild(newPrevBtn, prevBtn);
  nextBtn.parentNode.replaceChild(newNextBtn, nextBtn);

  // Previous page
  newPrevBtn.addEventListener('click', async () => {
    if (dashboardState.historyPage > 1) {
      dashboardState.historyPage--;
      await loadHistory();
    }
  });

  // Next page
  newNextBtn.addEventListener('click', async () => {
    if (dashboardState.historyPage < totalPages) {
      dashboardState.historyPage++;
      await loadHistory();
    }
  });

  // Disable buttons at boundaries
  newPrevBtn.disabled = dashboardState.historyPage <= 1;
  newNextBtn.disabled = dashboardState.historyPage >= totalPages;

  // Update button styles
  if (newPrevBtn.disabled) {
    newPrevBtn.classList.add('opacity-50', 'cursor-not-allowed');
  } else {
    newPrevBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  }

  if (newNextBtn.disabled) {
    newNextBtn.classList.add('opacity-50', 'cursor-not-allowed');
  } else {
    newNextBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  }
}

/**
 * Handle copy to clipboard button click
 * Copy all RESULT data to clipboard in tabular format
 * Requirements: 3.1, 3.8, 3.9
 */
async function handleCopyToClipboard() {
  try {
    // Check if there's data to copy
    if (!dashboardState.currentResults || dashboardState.currentResults.length === 0) {
      displayAlert('No data available to copy', 'warning');
      return;
    }

    // Get all unique field names across all transactions
    const allFields = new Set();
    dashboardState.currentResults.forEach(transaction => {
      Object.keys(transaction).forEach(field => allFields.add(field));
    });
    const fieldNames = Array.from(allFields);

    // Create header row
    let textData = fieldNames.join('\t') + '\n';

    // Create data rows (one row per transaction)
    dashboardState.currentResults.forEach(transaction => {
      const row = fieldNames.map(field => transaction[field] || '').join('\t');
      textData += row + '\n';
    });

    // Use browser clipboard API (Requirement 3.1)
    await navigator.clipboard.writeText(textData);

    // Display success alert (Requirement 3.9)
    displayAlert('Data copied to clipboard successfully!', 'success');
  } catch (error) {
    console.error('Error copying to clipboard:', error);
    
    // Display error alert (Requirement 3.8)
    displayAlert(
      error.message || 'Failed to copy data to clipboard. Please try again.',
      'error'
    );
  }
}

/**
 * Handle export to CSV button click
 * Generate CSV file from RESULT data in tabular format and trigger browser download
 * Requirements: 3.2, 3.8, 3.9
 */
async function handleExportToCSV() {
  try {
    // Check if there's data to export
    if (!dashboardState.currentResults || dashboardState.currentResults.length === 0) {
      displayAlert('No data available to export', 'warning');
      return;
    }

    // Check if Papa is available (PapaParse library)
    if (typeof Papa === 'undefined') {
      throw new Error('PapaParse library not loaded');
    }

    // currentResults is already an array of transaction objects
    // Each transaction will be a row, with field names as columns
    const csvData = dashboardState.currentResults;

    // Generate CSV using PapaParse (Requirement 3.2)
    const csv = Papa.unparse(csvData, {
      header: true,
      quotes: true, // Quote all fields for safety
      skipEmptyLines: false
    });

    // Create blob from CSV string
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `document-extraction-${timestamp}.csv`;

    // Trigger browser download (Requirement 3.2)
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up the URL object
    URL.revokeObjectURL(url);

    // Display success alert (Requirement 3.9)
    displayAlert('CSV file downloaded successfully!', 'success');
  } catch (error) {
    console.error('Error exporting to CSV:', error);
    
    // Display error alert (Requirement 3.8)
    displayAlert(
      error.message || 'Failed to export CSV file. Please try again.',
      'error'
    );
  }
}

/**
 * Handle export to XLSX button click
 * Generate XLSX file from RESULT data in tabular format and trigger browser download
 * Requirements: 3.3, 3.8, 3.9
 */
async function handleExportToXLSX() {
  try {
    // Check if there's data to export
    if (!dashboardState.currentResults || dashboardState.currentResults.length === 0) {
      displayAlert('No data available to export', 'warning');
      return;
    }

    // Check if XLSX is available (SheetJS library)
    if (typeof XLSX === 'undefined') {
      throw new Error('SheetJS library not loaded');
    }

    // currentResults is already an array of transaction objects
    // Each transaction will be a row, with field names as columns
    const xlsxData = dashboardState.currentResults;

    // Create a new workbook (Requirement 3.3)
    const workbook = XLSX.utils.book_new();

    // Convert data array to worksheet
    const worksheet = XLSX.utils.json_to_sheet(xlsxData);

    // Add worksheet to workbook with a name
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Extraction Results');

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `document-extraction-${timestamp}.xlsx`;

    // Trigger browser download using SheetJS writeFile method (Requirement 3.3)
    XLSX.writeFile(workbook, filename);

    // Display success alert (Requirement 3.9)
    displayAlert('XLSX file downloaded successfully!', 'success');
  } catch (error) {
    console.error('Error exporting to XLSX:', error);
    
    // Display error alert (Requirement 3.8)
    displayAlert(
      error.message || 'Failed to export XLSX file. Please try again.',
      'error'
    );
  }
}

/**
 * Handle export to JSON button click
 * Generate JSON file from RESULT data and trigger browser download
 * Requirements: 3.4, 3.8, 3.9
 */
async function handleExportToJSON() {
  try {
    // Check if there's data to export
    if (!dashboardState.currentResults || Object.keys(dashboardState.currentResults).length === 0) {
      displayAlert('No data available to export', 'warning');
      return;
    }

    // Generate JSON string from RESULT data (Requirement 3.4)
    // Use JSON.stringify with formatting for readability
    const jsonString = JSON.stringify(dashboardState.currentResults, null, 2);

    // Create blob from JSON string (Requirement 3.4)
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `document-extraction-${timestamp}.json`;

    // Trigger browser download using URL.createObjectURL (Requirement 3.4)
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up the URL object
    URL.revokeObjectURL(url);

    // Display success alert (Requirement 3.9)
    displayAlert('JSON file downloaded successfully!', 'success');
  } catch (error) {
    console.error('Error exporting to JSON:', error);
    
    // Display error alert (Requirement 3.8)
    displayAlert(
      error.message || 'Failed to export JSON file. Please try again.',
      'error'
    );
  }
}

/**
 * Handle export to FTP button click
 * Upload data to configured FTP server
 * Requirements: 3.5, 3.8, 3.9, 19.1, 19.2
 */
async function handleExportToFTP() {
  try {
    // Check if there's data to export
    if (!dashboardState.currentResults || Object.keys(dashboardState.currentResults).length === 0) {
      displayAlert('No data available to export', 'warning');
      return;
    }

    // Retrieve FTP configuration from Local Storage (Requirement 3.5, 19.1)
    const ftpSettings = await storageManager.getFTPSettings();
    
    if (!ftpSettings) {
      displayAlert('FTP configuration not found. Please configure FTP settings first.', 'warning');
      return;
    }

    // Validate FTP configuration
    if (!ftpSettings.host || !ftpSettings.username) {
      displayAlert('Incomplete FTP configuration. Please check your FTP settings.', 'warning');
      return;
    }

    // Generate CSV content from RESULT data
    // Using CSV format as the default export format for FTP
    const csvData = Object.entries(dashboardState.currentResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    // Check if Papa is available (PapaParse library)
    if (typeof Papa === 'undefined') {
      throw new Error('PapaParse library not loaded');
    }

    const csv = Papa.unparse(csvData, {
      header: true,
      quotes: true,
      skipEmptyLines: false
    });

    // Convert CSV to base64 for transmission
    const base64Content = btoa(unescape(encodeURIComponent(csv)));

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const fileName = `document-extraction-${timestamp}.csv`;

    // Call FTP API endpoint (Requirement 19.2)
    const response = await apiClient.uploadToFTP(
      fileName,
      base64Content,
      ftpSettings.remote_directory || ''
    );

    // Display success alert (Requirement 3.9)
    displayAlert(
      `File uploaded successfully to FTP server: ${fileName}`,
      'success'
    );
  } catch (error) {
    console.error('Error exporting to FTP:', error);
    
    // Display error alert (Requirement 3.8)
    displayAlert(
      error.message || 'Failed to upload file to FTP server. Please check your FTP configuration and try again.',
      'error'
    );
  }
}

/**
 * Submit data to configured external API
 * Requirements: 3.6, 3.8, 3.9
 */
async function handleSubmitToAPI() {
  try {
    // Check if there's data to submit
    if (!dashboardState.currentResults || Object.keys(dashboardState.currentResults).length === 0) {
      displayAlert('No data available to submit', 'warning');
      return;
    }

    // Retrieve API configuration from Local Storage (Requirement 3.6)
    const apiSettings = await storageManager.getAPISettings();
    
    if (!apiSettings) {
      displayAlert('API configuration not found. Please configure API settings first.', 'warning');
      return;
    }

    // Validate API configuration
    if (!apiSettings.endpoint) {
      displayAlert('Incomplete API configuration. Please check your API settings.', 'warning');
      return;
    }

    // Validate method
    const method = apiSettings.method || 'POST';
    if (!['GET', 'POST'].includes(method)) {
      displayAlert('Invalid API method. Only GET and POST are supported.', 'warning');
      return;
    }

    // Prepare the data to send
    const dataToSend = dashboardState.currentResults;

    // Parse headers if provided
    let headers = {
      'Content-Type': 'application/json'
    };
    
    if (apiSettings.headers) {
      try {
        // If headers is a string, parse it as JSON
        const customHeaders = typeof apiSettings.headers === 'string' 
          ? JSON.parse(apiSettings.headers) 
          : apiSettings.headers;
        headers = { ...headers, ...customHeaders };
      } catch (error) {
        console.warn('Failed to parse custom headers:', error);
        displayAlert('Invalid header format in API configuration. Using default headers.', 'warning');
      }
    }

    // Prepare request options
    const options = {
      method: method,
      headers: headers
    };

    // For POST requests, include body
    if (method === 'POST') {
      // If custom body template is provided, use it; otherwise send the data directly
      if (apiSettings.body) {
        try {
          // Replace placeholders in body template with actual data
          let bodyTemplate = apiSettings.body;
          
          // Simple placeholder replacement: {{fieldName}} with actual values
          Object.entries(dataToSend).forEach(([field, value]) => {
            const placeholder = new RegExp(`{{${field}}}`, 'g');
            bodyTemplate = bodyTemplate.replace(placeholder, value || '');
          });
          
          options.body = bodyTemplate;
        } catch (error) {
          console.warn('Failed to process body template:', error);
          // Fallback to sending data as JSON
          options.body = JSON.stringify(dataToSend);
        }
      } else {
        // Default: send data as JSON
        options.body = JSON.stringify(dataToSend);
      }
    }

    // Send data to configured endpoint (Requirement 3.6)
    const response = await fetch(apiSettings.endpoint, options);

    // Check response status
    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}: ${response.statusText}`);
    }

    // Try to parse response
    let responseData;
    try {
      responseData = await response.json();
    } catch (error) {
      // Response might not be JSON, that's okay
      responseData = await response.text();
    }

    // Display success alert (Requirement 3.9)
    displayAlert(
      'Data submitted successfully to external API',
      'success'
    );
  } catch (error) {
    console.error('Error submitting to API:', error);
    
    // Display error alert (Requirement 3.8)
    displayAlert(
      error.message || 'Failed to submit data to external API. Please check your API configuration and try again.',
      'error'
    );
  }
}

/**
 * Send email with extracted data as attachments
 * Requirements: 3.7, 3.8, 3.9, 18.1, 18.2, 18.3, 18.7, 18.8, 18.9
 */
async function handleSendEmail() {
  try {
    // Check if there's data to send
    if (!dashboardState.currentResults || Object.keys(dashboardState.currentResults).length === 0) {
      displayAlert('No data available to send', 'warning');
      return;
    }

    // Retrieve email configuration from Local Storage (Requirement 3.7, 18.1, 18.2)
    const emailSettings = await storageManager.getEmailSettings();
    
    if (!emailSettings) {
      displayAlert('Email configuration not found. Please configure email settings first.', 'warning');
      return;
    }

    // Validate email configuration
    if (!emailSettings.to) {
      displayAlert('Incomplete email configuration. Please specify recipient email address.', 'warning');
      return;
    }

    // Validate email mode
    const mode = emailSettings.mode || 'default';
    
    if (mode === 'smtp') {
      // Use SMTP mode with smtp.js (Requirement 18.2)
      await sendEmailViaSMTP(emailSettings);
    } else {
      // Use default server mode with API call (Requirement 18.1)
      await sendEmailViaAPI(emailSettings);
    }
  } catch (error) {
    console.error('Error sending email:', error);
    
    // Display error alert (Requirement 3.8, 18.9)
    displayAlert(
      error.message || 'Failed to send email. Please check your email configuration and try again.',
      'error'
    );
  }
}

/**
 * Send email via default server (API call)
 * Requirements: 18.1, 18.3, 18.7, 18.8, 18.9
 */
async function sendEmailViaAPI(emailSettings) {
  // Generate attachments in selected formats (Requirement 18.3)
  const attachments = await generateEmailAttachments(emailSettings.attachment_formats || ['csv']);
  
  // Call send_email API endpoint (Requirement 18.1)
  const response = await apiClient.sendEmail(
    emailSettings.to,
    emailSettings.cc || '',
    emailSettings.subject || 'Document Extraction Results',
    attachments
  );

  // Display success alert (Requirement 3.9, 18.8)
  displayAlert(
    'Email sent successfully via default server',
    'success'
  );
}

/**
 * Send email via SMTP using smtp.js library
 * Requirements: 18.2, 18.3, 18.7, 18.8, 18.9
 */
async function sendEmailViaSMTP(emailSettings) {
  // Check if smtp.js is loaded
  if (typeof Email === 'undefined') {
    throw new Error('SMTP library (smtp.js) not loaded. Please ensure smtp.js is included in the extension.');
  }

  // Validate SMTP configuration
  if (!emailSettings.smtp_server || !emailSettings.smtp_username || !emailSettings.smtp_password) {
    throw new Error('Incomplete SMTP configuration. Please configure SMTP server, username, and password.');
  }

  // Generate attachments in selected formats (Requirement 18.3)
  const attachments = await generateEmailAttachments(emailSettings.attachment_formats || ['csv']);
  
  // Prepare SMTP email
  const emailData = {
    SecureToken: emailSettings.smtp_password, // For smtp.js with secure token
    To: emailSettings.to,
    From: emailSettings.email_from || emailSettings.smtp_username,
    Subject: emailSettings.subject || 'Document Extraction Results',
    Body: 'Please find attached the document extraction results.',
    Attachments: attachments.map(att => ({
      name: att.fileName,
      data: att.fileContent
    }))
  };

  // Add CC if provided
  if (emailSettings.cc) {
    emailData.Cc = emailSettings.cc;
  }

  // Send email using smtp.js (Requirement 18.2)
  await Email.send(emailData);

  // Display success alert (Requirement 3.9, 18.8)
  displayAlert(
    'Email sent successfully via SMTP',
    'success'
  );
}

/**
 * Generate email attachments in selected formats
 * Requirements: 18.3, 18.4, 18.5, 18.6, 18.7
 */
async function generateEmailAttachments(formats) {
  const attachments = [];
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  
  // Convert RESULT data to array format
  const dataArray = Object.entries(dashboardState.currentResults).map(([field, value]) => ({
    Field: field,
    Value: value || ''
  }));

  // Generate CSV attachment (Requirement 18.4)
  if (formats.includes('csv')) {
    if (typeof Papa === 'undefined') {
      throw new Error('PapaParse library not loaded');
    }
    
    const csv = Papa.unparse(dataArray, {
      header: true,
      quotes: true,
      skipEmptyLines: false
    });
    
    const base64Content = btoa(unescape(encodeURIComponent(csv)));
    
    attachments.push({
      fileName: `document-extraction-${timestamp}.csv`,
      fileContent: base64Content
    });
  }

  // Generate XLSX attachment (Requirement 18.5)
  if (formats.includes('xlsx')) {
    if (typeof XLSX === 'undefined') {
      throw new Error('XLSX library not loaded');
    }
    
    const worksheet = XLSX.utils.json_to_sheet(dataArray);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Results');
    
    const xlsxBinary = XLSX.write(workbook, { bookType: 'xlsx', type: 'binary' });
    
    // Convert binary string to base64
    const xlsxBase64 = btoa(xlsxBinary);
    
    attachments.push({
      fileName: `document-extraction-${timestamp}.xlsx`,
      fileContent: xlsxBase64
    });
  }

  // Generate JSON attachment (Requirement 18.6)
  if (formats.includes('json')) {
    const jsonContent = JSON.stringify(dashboardState.currentResults, null, 2);
    const base64Content = btoa(unescape(encodeURIComponent(jsonContent)));
    
    attachments.push({
      fileName: `document-extraction-${timestamp}.json`,
      fileContent: base64Content
    });
  }

  // Ensure at least one attachment format is generated (Requirement 18.7)
  if (attachments.length === 0) {
    throw new Error('No attachment formats selected. Please select at least one format (CSV, XLSX, or JSON).');
  }

  return attachments;
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', initDashboard);
