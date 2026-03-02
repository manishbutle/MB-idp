/**
 * Prompts/Datapoints Tab Script
 * Handles prompt management functionality
 */

// Track if prompts have been loaded in this session
let promptsLoaded = false;

/**
 * Initialize Prompts/Datapoints tab
 */
function initPromptsTab() {
  console.log('Initializing Prompts/Datapoints tab');
  
  // Set up event listeners
  setupPromptsEventListeners();
  
  // Set up modal event listeners
  setupModalEventListeners();
  
  // Don't load prompts immediately - wait for tab to be visible
  // Prompts will be loaded when user clicks on the Prompts tab
}

/**
 * Load prompts when tab becomes visible
 * This function is called from popup.js when the prompts tab is clicked
 */
function onPromptsTabVisible() {
  console.log('[Prompts] onPromptsTabVisible() called - Prompts tab is now visible');
  
  try {
    console.log('[Prompts] About to call loadPromptsTableData()...');
    
    // Call loadPromptsTableData and handle the promise
    loadPromptsTableData().then((prompts) => {
      console.log('[Prompts] loadPromptsTableData() completed successfully');
      console.log('[Prompts] Loaded prompts:', prompts);
    }).catch((error) => {
      console.error('[Prompts] loadPromptsTableData() failed:', error);
    });
    
    console.log('[Prompts] loadPromptsTableData() called (promise returned)');
  } catch (error) {
    console.error('[Prompts] Error calling loadPromptsTableData():', error);
  }
}

/**
 * Set up event listeners for prompts tab
 */
function setupPromptsEventListeners() {
  // Add New button
  const addBtn = document.getElementById('add-prompt-btn');
  if (addBtn) {
    addBtn.addEventListener('click', handleAddPrompt);
  }
  
  // Reset button
  const resetBtn = document.getElementById('reset-prompts-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', handleResetPrompts);
  }
  
  // Export to CSV button
  const exportBtn = document.getElementById('export-prompts-csv-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', handleExportPromptsToCSV);
  }
}

/**
 * Load prompts from cache or API
 * Implements caching strategy: try cache first, then API, with fallback
 * Requirements: 4.1, 4.2
 */
async function loadPromptsTableData() {
  console.log('[Prompts] loadPrompts() called');
  
  // Check if required dependencies are available
  if (typeof storageManager === 'undefined') {
    console.error('[Prompts] storageManager is not defined!');
    displayAlert('Storage manager not available. Please reload the extension.', 'error');
    return;
  }
  
  if (typeof apiClient === 'undefined') {
    console.error('[Prompts] apiClient is not defined!');
    displayAlert('API client not available. Please reload the extension.', 'error');
    return;
  }
  
  console.log('[Prompts] Dependencies check passed');
  
  try {
    showLoading();
    console.log('[Prompts] Loading indicator shown');
    
    // Try to load from cache first for immediate display
    console.log('[Prompts] Attempting to load from cache...');
    const cachedData = await storageManager.getPrompts();
    console.log('[Prompts] Cache data:', cachedData);
    
    if (cachedData && cachedData.prompts && cachedData.prompts.length > 0) {
      // Display cached data immediately
      console.log('[Prompts] Found cached prompts:', cachedData.prompts.length);
      populatePromptsTable(cachedData.prompts);
      console.log('[Prompts] Table populated with cached data');
      hideLoading();
      
      // Return cached data without API refresh
      return cachedData.prompts;
    }
    
    // No cache available, must fetch from API
    console.log('[Prompts] No cache found, fetching from API...');
    try {
      const apiData = await apiClient.getDatapoints();
      console.log('[Prompts] API response:', apiData);
      
      if (apiData && apiData.prompts && apiData.prompts.length > 0) {
        // Store in cache
        await storageManager.setPrompts(apiData.prompts);
        console.log('[Prompts] Saved to cache');
        
        // Display data
        populatePromptsTable(apiData.prompts);
        console.log('[Prompts] Loaded prompts from API:', apiData.prompts.length);
        return apiData.prompts;
      } else {
        // No data from API
        console.log('[Prompts] No prompts returned from API');
        showEmptyPromptsState();
        displayAlert('No prompts available. Click "Reset" to load from server.', 'info');
      }
    } catch (apiError) {
      // API call failed and no cache
      console.error('[Prompts] Failed to load from API:', apiError);
      showEmptyPromptsState();
      displayAlert('Failed to load prompts. Please check your connection.', 'error');
    }
    
    hideLoading();
  } catch (error) {
    hideLoading();
    console.error('[Prompts] Error in loadPrompts():', error);
    console.error('[Prompts] Error stack:', error.stack);
    showEmptyPromptsState();
    displayAlert('Failed to load prompts. Please try again.', 'error');
  }
}

/**
 * Load prompts and populate table
 * @deprecated Use loadPrompts() instead
 */
async function loadPromptsTable() {
  return loadPromptsTableData();
}

/**
 * Populate prompts table with data
 * @param {Array} prompts - Array of prompt objects
 */
function populatePromptsTable(prompts) {
  console.log('[Prompts] populatePromptsTable() called with', prompts?.length, 'prompts');
  
  const tbody = document.getElementById('prompts-table-body');
  if (!tbody) {
    console.error('[Prompts] Table body element not found!');
    return;
  }
  
  console.log('[Prompts] Table body element found');
  
  // Clear existing rows
  tbody.innerHTML = '';
  console.log('[Prompts] Table cleared');
  
  // Add rows for each prompt
  prompts.forEach((prompt, index) => {
    console.log(`[Prompts] Creating row ${index + 1}:`, prompt.prompt_name);
    const row = createPromptRow(prompt);
    tbody.appendChild(row);
  });
  
  console.log('[Prompts] Table population complete');
}

/**
 * Create a table row for a prompt
 * @param {Object} prompt - Prompt object
 * @returns {HTMLElement} Table row element
 */
function createPromptRow(prompt) {
  const row = document.createElement('tr');
  row.className = 'hover:bg-gray-50';
  
  // Prompt Name cell
  const nameCell = document.createElement('td');
  nameCell.className = 'border border-gray-300 px-4 py-2';
  nameCell.textContent = prompt.prompt_name || '';
  row.appendChild(nameCell);
  
  // Description cell
  const descCell = document.createElement('td');
  descCell.className = 'border border-gray-300 px-4 py-2';
  descCell.textContent = prompt.description || '';
  row.appendChild(descCell);
  
  // Actions cell
  const actionsCell = document.createElement('td');
  actionsCell.className = 'border border-gray-300 px-4 py-2 text-center';
  
  // Edit button with icon
  const editBtn = document.createElement('button');
  editBtn.className = 'bg-blue-600 hover:bg-blue-700 text-white p-2 rounded mr-2 transition-colors';
  editBtn.title = 'Edit';
  editBtn.innerHTML = `
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
    </svg>
  `;
  editBtn.onclick = () => handleEditPrompt(prompt);
  actionsCell.appendChild(editBtn);
  
  // Delete button with icon
  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'bg-red-600 hover:bg-red-700 text-white p-2 rounded transition-colors';
  deleteBtn.title = 'Delete';
  deleteBtn.innerHTML = `
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
    </svg>
  `;
  deleteBtn.onclick = () => handleDeletePrompt(prompt);
  actionsCell.appendChild(deleteBtn);
  
  row.appendChild(actionsCell);
  
  return row;
}

/**
 * Show empty state when no prompts are available
 */
function showEmptyPromptsState() {
  const tbody = document.getElementById('prompts-table-body');
  if (!tbody) return;
  
  tbody.innerHTML = `
    <tr>
      <td colspan="3" class="border border-gray-300 px-4 py-8 text-center text-gray-500">
        No prompts available. Click "Add New" to create a prompt or "Reset" to load from server.
      </td>
    </tr>
  `;
}

/**
 * Handle Add New button click
 * Requirements: 4.5
 */
function handleAddPrompt() {
  showPromptModal();
}

/**
 * Handle Edit button click
 * @param {Object} prompt - Prompt object to edit
 * Requirements: 4.9
 */
function handleEditPrompt(prompt) {
  showPromptModal(prompt);
}

/**
 * Handle Delete button click
 * @param {Object} prompt - Prompt object to delete
 * Requirements: 4.10
 */
async function handleDeletePrompt(prompt) {
  // Show confirmation dialog
  const confirmed = confirm(`Are you sure you want to delete the prompt "${prompt.prompt_name}"?\n\nThis action cannot be undone.`);
  
  if (!confirmed) {
    return;
  }
  
  try {
    showLoading();
    
    // Delete from Local_Storage
    await deletePrompt(prompt.prompt_id);
    
    // Reload the table from local storage to show changes immediately
    const updatedData = await storageManager.getPrompts();
    if (updatedData && updatedData.prompts) {
      populatePromptsTable(updatedData.prompts);
      console.log('Table refreshed after deletion');
    } else {
      showEmptyPromptsState();
    }
    
    hideLoading();
    displayAlert('Prompt deleted successfully', 'success');
  } catch (error) {
    hideLoading();
    console.error('Error deleting prompt:', error);
    displayAlert('Failed to delete prompt', 'error');
  }
}

/**
 * Handle Reset button click
 * Calls reset_prompts API and refreshes Local_Storage cache
 * Requirements: 4.7
 */
async function handleResetPrompts() {
  // Show confirmation dialog
  const confirmed = confirm('Are you sure you want to reset all prompts?\n\nThis will reload prompts from the server and replace your local cache.');
  
  if (!confirmed) {
    return;
  }
  
  try {
    showLoading();
    
    // Call reset_prompts API
    const apiData = await apiClient.resetPrompts();
    
    if (apiData && apiData.prompts && apiData.prompts.length > 0) {
      // Replace Local_Storage cache with fresh data
      await storageManager.setPrompts(apiData.prompts);
      
      // Reload the table
      populatePromptsTable(apiData.prompts);
      
      console.log('Prompts reset successfully:', apiData.prompts.length, 'prompts');
      displayAlert('Prompts reset successfully', 'success');
    } else {
      // No data from API
      showEmptyPromptsState();
      displayAlert('No prompts available from server', 'warning');
    }
    
    hideLoading();
  } catch (error) {
    hideLoading();
    console.error('Error resetting prompts:', error);
    displayAlert(`Failed to reset prompts: ${error.message}`, 'error');
  }
}

/**
 * Handle Export to CSV button click
 * Exports all prompts to a CSV file
 * Requirements: 4.8
 */
async function handleExportPromptsToCSV() {
  try {
    const promptsData = await storageManager.getPrompts();
    
    if (!promptsData || !promptsData.prompts || promptsData.prompts.length === 0) {
      displayAlert('No prompts to export', 'warning');
      return;
    }
    
    // Prepare data for CSV export
    const csvData = promptsData.prompts.map(prompt => ({
      'Prompt Name': prompt.prompt_name || '',
      'Description': prompt.description || '',
      'Prompt': prompt.prompt || '',
      'Created By': prompt.created_by || '',
      'Created Date': prompt.created_date || '',
      'Modified By': prompt.modified_by || '',
      'Modified Date': prompt.modified_date || ''
    }));
    
    // Convert to CSV using PapaParse
    const csv = Papa.unparse(csvData);
    
    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `prompts_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    
    displayAlert('Prompts exported to CSV successfully', 'success');
  } catch (error) {
    console.error('Error exporting prompts to CSV:', error);
    displayAlert('Failed to export prompts to CSV', 'error');
  }
}

/**
 * Show prompt modal for add or edit
 * @param {Object} prompt - Prompt object to edit (optional, for edit mode)
 */
function showPromptModal(prompt = null) {
  const modal = document.getElementById('prompt-modal');
  const title = document.getElementById('prompt-modal-title');
  const form = document.getElementById('prompt-form');
  
  if (!modal || !title || !form) return;
  
  // Set modal title
  title.textContent = prompt ? 'Edit Prompt' : 'Add New Prompt';
  
  // Reset form
  form.reset();
  
  // If editing, populate form with existing data
  if (prompt) {
    document.getElementById('prompt-id').value = prompt.prompt_id || '';
    document.getElementById('prompt-name').value = prompt.prompt_name || '';
    document.getElementById('prompt-description').value = prompt.description || '';
    document.getElementById('prompt-text').value = prompt.prompt || '';
  } else {
    document.getElementById('prompt-id').value = '';
  }
  
  // Show modal
  modal.classList.remove('hidden');
}

/**
 * Hide prompt modal
 */
function hidePromptModal() {
  const modal = document.getElementById('prompt-modal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

/**
 * Handle prompt form submission
 * @param {Event} event - Form submit event
 */
async function handlePromptFormSubmit(event) {
  event.preventDefault();
  
  try {
    showLoading();
    
    // Get form data
    const promptId = document.getElementById('prompt-id').value;
    const promptName = document.getElementById('prompt-name').value.trim();
    const description = document.getElementById('prompt-description').value.trim();
    const promptText = document.getElementById('prompt-text').value.trim();
    
    // Validate
    if (!promptName || !description || !promptText) {
      displayAlert('Please fill in all required fields', 'error');
      hideLoading();
      return;
    }
    
    // Create prompt object
    const promptData = {
      prompt_id: promptId || generateUUID(),
      prompt_name: promptName,
      description: description,
      prompt: promptText,
      modified_date: new Date().toISOString()
    };
    
    // If new prompt, set created fields
    if (!promptId) {
      promptData.created_date = promptData.modified_date;
      promptData.created_by = 'user'; // TODO: Get from session
      promptData.modified_by = 'user';
    } else {
      promptData.modified_by = 'user'; // TODO: Get from session
    }
    
    // Save or update
    if (promptId) {
      await editPrompt(promptId, promptData);
      displayAlert('Prompt updated successfully', 'success');
    } else {
      await addPrompt(promptData);
      displayAlert('Prompt created successfully', 'success');
    }
    
    // Hide modal
    hidePromptModal();
    
    // Reload table from local storage to show changes immediately
    const updatedData = await storageManager.getPrompts();
    if (updatedData && updatedData.prompts) {
      populatePromptsTable(updatedData.prompts);
      console.log('Table refreshed with updated prompts');
    }
    
    hideLoading();
  } catch (error) {
    hideLoading();
    console.error('Error saving prompt:', error);
    displayAlert('Failed to save prompt', 'error');
  }
}

/**
 * Add a new prompt to Local_Storage
 * @param {Object} promptData - Prompt object to add
 * Requirements: 4.6
 */
async function addPrompt(promptData) {
  try {
    // Get existing prompts
    const existingData = await storageManager.getPrompts();
    const prompts = existingData?.prompts || [];
    
    // Add new prompt
    prompts.push(promptData);
    
    // Save to Local_Storage
    await storageManager.setPrompts(prompts);
    
    console.log('Prompt added:', promptData.prompt_id);
  } catch (error) {
    console.error('Error adding prompt:', error);
    throw error;
  }
}

/**
 * Edit an existing prompt in Local_Storage
 * @param {string} promptId - ID of prompt to edit
 * @param {Object} promptData - Updated prompt object
 * Requirements: 4.9
 */
async function editPrompt(promptId, promptData) {
  try {
    // Get existing prompts
    const existingData = await storageManager.getPrompts();
    const prompts = existingData?.prompts || [];
    
    // Find and update prompt
    const index = prompts.findIndex(p => p.prompt_id === promptId);
    
    if (index === -1) {
      throw new Error('Prompt not found');
    }
    
    // Preserve created fields
    promptData.created_by = prompts[index].created_by;
    promptData.created_date = prompts[index].created_date;
    
    // Update prompt
    prompts[index] = promptData;
    
    // Save to Local_Storage
    await storageManager.setPrompts(prompts);
    
    console.log('Prompt updated:', promptId);
  } catch (error) {
    console.error('Error editing prompt:', error);
    throw error;
  }
}

/**
 * Delete a prompt from Local_Storage
 * @param {string} promptId - ID of prompt to delete
 * Requirements: 4.10
 */
async function deletePrompt(promptId) {
  try {
    // Get existing prompts
    const existingData = await storageManager.getPrompts();
    const prompts = existingData?.prompts || [];
    
    // Filter out the prompt to delete
    const updatedPrompts = prompts.filter(p => p.prompt_id !== promptId);
    
    if (updatedPrompts.length === prompts.length) {
      throw new Error('Prompt not found');
    }
    
    // Save to Local_Storage
    await storageManager.setPrompts(updatedPrompts);
    
    console.log('Prompt deleted:', promptId);
  } catch (error) {
    console.error('Error deleting prompt:', error);
    throw error;
  }
}

/**
 * Generate a UUID v4
 * @returns {string} UUID string
 */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Set up modal event listeners
 */
function setupModalEventListeners() {
  // Close button
  const closeBtn = document.getElementById('prompt-modal-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', hidePromptModal);
  }
  
  // Cancel button
  const cancelBtn = document.getElementById('prompt-modal-cancel');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', hidePromptModal);
  }
  
  // Form submit
  const form = document.getElementById('prompt-form');
  if (form) {
    form.addEventListener('submit', handlePromptFormSubmit);
  }
  
  // Click outside modal to close
  const modal = document.getElementById('prompt-modal');
  if (modal) {
    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        hidePromptModal();
      }
    });
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  initPromptsTab();
});

// Expose functions to window for testing
if (typeof window !== 'undefined') {
  window.onPromptsTabVisible = onPromptsTabVisible;
  window.loadPromptsTableData = loadPromptsTableData;
  window.loadPromptsTable = loadPromptsTable;
  window.populatePromptsTable = populatePromptsTable;
  window.createPromptRow = createPromptRow;
  window.showEmptyPromptsState = showEmptyPromptsState;
  window.handleAddPrompt = handleAddPrompt;
  window.handleEditPrompt = handleEditPrompt;
  window.handleDeletePrompt = handleDeletePrompt;
  window.handleResetPrompts = handleResetPrompts;
  window.handleExportPromptsToCSV = handleExportPromptsToCSV;
  window.addPrompt = addPrompt;
  window.editPrompt = editPrompt;
  window.deletePrompt = deletePrompt;
  window.showPromptModal = showPromptModal;
  window.hidePromptModal = hidePromptModal;
  window.handlePromptFormSubmit = handlePromptFormSubmit;
  window.generateUUID = generateUUID;
}
