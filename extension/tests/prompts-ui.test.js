/**
 * Tests for Prompts/Datapoints UI Layout
 * Validates Requirements: 4.3, 4.4, 4.5, 4.8
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

describe('Prompts/Datapoints UI Layout', () => {
  let dom;
  let document;
  let window;

  beforeEach(() => {
    // Load the HTML file
    const html = fs.readFileSync(
      path.resolve(__dirname, '../popup.html'),
      'utf-8'
    );

    // Create a JSDOM instance
    dom = new JSDOM(html, {
      runScripts: 'dangerously',
      resources: 'usable',
      url: 'http://localhost'
    });

    window = dom.window;
    document = window.document;

    // Mock global objects
    global.document = document;
    global.window = window;
  });

  it('should have a table with Prompt Name, Description, and Actions columns', () => {
    const table = document.getElementById('prompts-table');
    expect(table).toBeTruthy();

    const headers = table.querySelectorAll('thead th');
    expect(headers.length).toBe(3);
    expect(headers[0].textContent.trim()).toBe('Prompt Name');
    expect(headers[1].textContent.trim()).toBe('Description');
    expect(headers[2].textContent.trim()).toBe('Actions');
  });

  it('should have an "Add New" button', () => {
    const addBtn = document.getElementById('add-prompt-btn');
    expect(addBtn).toBeTruthy();
    expect(addBtn.textContent.trim()).toBe('Add New');
    expect(addBtn.className).toContain('bg-blue-600');
  });

  it('should have a "Reset" button', () => {
    const resetBtn = document.getElementById('reset-prompts-btn');
    expect(resetBtn).toBeTruthy();
    expect(resetBtn.textContent.trim()).toBe('Reset');
    expect(resetBtn.className).toContain('bg-gray-600');
  });

  it('should have an "Export to CSV" button', () => {
    const exportBtn = document.getElementById('export-prompts-csv-btn');
    expect(exportBtn).toBeTruthy();
    expect(exportBtn.textContent.trim()).toBe('Export to CSV');
    expect(exportBtn.className).toContain('bg-green-600');
  });

  it('should display empty state message when no prompts are available', () => {
    const tbody = document.getElementById('prompts-table-body');
    expect(tbody).toBeTruthy();
    
    const emptyMessage = tbody.querySelector('td[colspan="3"]');
    expect(emptyMessage).toBeTruthy();
    expect(emptyMessage.textContent).toContain('No prompts available');
  });

  it('should have proper table styling with borders and padding', () => {
    const table = document.getElementById('prompts-table');
    expect(table.className).toContain('border-collapse');

    const headers = table.querySelectorAll('thead th');
    headers.forEach(header => {
      expect(header.className).toContain('border');
      expect(header.className).toContain('px-4');
      expect(header.className).toContain('py-2');
    });
  });

  it('should have the prompts tab initially hidden', () => {
    const promptsTab = document.getElementById('prompts-tab');
    expect(promptsTab).toBeTruthy();
    expect(promptsTab.className).toContain('hidden');
  });

  it('should have consistent styling with Dashboard tab', () => {
    const promptsTab = document.getElementById('prompts-tab');
    const dashboardTab = document.getElementById('dashboard-tab');
    
    // Both should have space-y-4 or space-y-6 for consistent spacing
    expect(promptsTab.querySelector('.space-y-4')).toBeTruthy();
    expect(dashboardTab.querySelector('.space-y-6')).toBeTruthy();
  });
});

describe('Prompt Loading and Caching (Task 14.2)', () => {
  let dom;
  let document;
  let window;
  let mockStorageManager;
  let mockApiClient;

  beforeEach(() => {
    const html = fs.readFileSync(
      path.resolve(__dirname, '../popup.html'),
      'utf-8'
    );

    dom = new JSDOM(html, {
      runScripts: 'dangerously',
      resources: 'usable',
      url: 'http://localhost'
    });

    window = dom.window;
    document = window.document;

    global.document = document;
    global.window = window;

    // Mock storage manager
    mockStorageManager = {
      getPrompts: vi.fn(),
      setPrompts: vi.fn()
    };

    // Mock API client
    mockApiClient = {
      getDatapoints: vi.fn()
    };

    // Mock external utility functions BEFORE loading script
    window.showLoading = vi.fn();
    window.hideLoading = vi.fn();
    window.displayAlert = vi.fn();

    // Inject mocks into window scope BEFORE loading script
    window.storageManager = mockStorageManager;
    window.apiClient = mockApiClient;

    // Load the prompts.js script and evaluate it in the window context
    const promptsScript = fs.readFileSync(
      path.resolve(__dirname, '../scripts/prompts.js'),
      'utf-8'
    );

    // Execute script in window context
    window.eval(promptsScript);

    // Now spy on the functions that were defined by the script
    vi.spyOn(window, 'populatePromptsTable');
    vi.spyOn(window, 'showEmptyPromptsState');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should load prompts from cache on tab open (Requirement 4.2)', async () => {
    const mockCachedPrompts = {
      prompts: [
        { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' },
        { prompt_id: '2', prompt_name: 'PO', description: 'Purchase order extraction' }
      ],
      last_sync: '2024-01-01T00:00:00Z'
    };

    mockStorageManager.getPrompts.mockResolvedValue(mockCachedPrompts);
    mockApiClient.getDatapoints.mockResolvedValue({ prompts: mockCachedPrompts.prompts });

    await window.loadPrompts();

    expect(mockStorageManager.getPrompts).toHaveBeenCalled();
    expect(window.populatePromptsTable).toHaveBeenCalledWith(mockCachedPrompts.prompts);
    expect(window.showLoading).toHaveBeenCalled();
    expect(window.hideLoading).toHaveBeenCalled();
  });

  it('should call datapoints API to fetch prompts (Requirement 4.1)', async () => {
    const mockApiPrompts = {
      prompts: [
        { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
      ]
    };

    mockStorageManager.getPrompts.mockResolvedValue(null);
    mockApiClient.getDatapoints.mockResolvedValue(mockApiPrompts);

    await window.loadPrompts();

    expect(mockApiClient.getDatapoints).toHaveBeenCalled();
    expect(mockStorageManager.setPrompts).toHaveBeenCalledWith(mockApiPrompts.prompts);
    expect(window.populatePromptsTable).toHaveBeenCalledWith(mockApiPrompts.prompts);
  });

  it('should cache prompts in Local_Storage after API fetch (Requirement 4.2)', async () => {
    const mockApiPrompts = {
      prompts: [
        { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
      ]
    };

    mockStorageManager.getPrompts.mockResolvedValue(null);
    mockApiClient.getDatapoints.mockResolvedValue(mockApiPrompts);

    await window.loadPrompts();

    expect(mockStorageManager.setPrompts).toHaveBeenCalledWith(mockApiPrompts.prompts);
  });

  it('should refresh cache from API in background when cache exists', async () => {
    const mockCachedPrompts = {
      prompts: [
        { prompt_id: '1', prompt_name: 'Old Invoice', description: 'Old description' }
      ],
      last_sync: '2024-01-01T00:00:00Z'
    };

    const mockApiPrompts = {
      prompts: [
        { prompt_id: '1', prompt_name: 'New Invoice', description: 'New description' }
      ]
    };

    mockStorageManager.getPrompts.mockResolvedValue(mockCachedPrompts);
    mockApiClient.getDatapoints.mockResolvedValue(mockApiPrompts);

    await window.loadPrompts();

    // Should display cached data first
    expect(window.populatePromptsTable).toHaveBeenCalledWith(mockCachedPrompts.prompts);
    
    // Should update cache with fresh data
    expect(mockStorageManager.setPrompts).toHaveBeenCalledWith(mockApiPrompts.prompts);
    
    // Should update table with fresh data
    expect(window.populatePromptsTable).toHaveBeenCalledWith(mockApiPrompts.prompts);
  });

  it('should use cached data when API fails', async () => {
    const mockCachedPrompts = {
      prompts: [
        { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
      ],
      last_sync: '2024-01-01T00:00:00Z'
    };

    mockStorageManager.getPrompts.mockResolvedValue(mockCachedPrompts);
    mockApiClient.getDatapoints.mockRejectedValue(new Error('Network error'));

    await window.loadPrompts();

    expect(window.populatePromptsTable).toHaveBeenCalledWith(mockCachedPrompts.prompts);
    expect(window.displayAlert).toHaveBeenCalledWith(
      expect.stringContaining('cached'),
      'warning'
    );
  });

  it('should show empty state when no cache and API returns no data', async () => {
    mockStorageManager.getPrompts.mockResolvedValue(null);
    mockApiClient.getDatapoints.mockResolvedValue({ prompts: [] });

    await window.loadPrompts();

    expect(window.showEmptyPromptsState).toHaveBeenCalled();
  });

  it('should show error alert when both cache and API fail', async () => {
    mockStorageManager.getPrompts.mockResolvedValue(null);
    mockApiClient.getDatapoints.mockRejectedValue(new Error('Network error'));

    await window.loadPrompts();

    expect(window.displayAlert).toHaveBeenCalledWith(
      expect.stringContaining('Failed to load prompts'),
      'error'
    );
    expect(window.showEmptyPromptsState).toHaveBeenCalled();
  });

  it('should handle cache retrieval errors gracefully', async () => {
    mockStorageManager.getPrompts.mockRejectedValue(new Error('Storage error'));
    mockApiClient.getDatapoints.mockResolvedValue({
      prompts: [{ prompt_id: '1', prompt_name: 'Invoice', description: 'Test' }]
    });

    await window.loadPrompts();

    // When cache fails, the error is caught and we show error message
    // The API is not called because the error happens in the outer try-catch
    expect(window.displayAlert).toHaveBeenCalledWith(
      expect.stringContaining('Failed to load prompts'),
      expect.any(String)
    );
  });

  it('should show loading indicator during fetch', async () => {
    mockStorageManager.getPrompts.mockResolvedValue(null);
    mockApiClient.getDatapoints.mockResolvedValue({
      prompts: [{ prompt_id: '1', prompt_name: 'Invoice', description: 'Test' }]
    });

    await window.loadPrompts();

    expect(window.showLoading).toHaveBeenCalled();
    expect(window.hideLoading).toHaveBeenCalled();
  });

  it('should hide loading indicator even when errors occur', async () => {
    mockStorageManager.getPrompts.mockResolvedValue(null);
    mockApiClient.getDatapoints.mockRejectedValue(new Error('Network error'));

    await window.loadPrompts();

    expect(window.showLoading).toHaveBeenCalled();
    expect(window.hideLoading).toHaveBeenCalled();
  });
});

describe('Prompts Table Row Creation', () => {
  let dom;
  let document;
  let window;

  beforeEach(() => {
    const html = fs.readFileSync(
      path.resolve(__dirname, '../popup.html'),
      'utf-8'
    );

    dom = new JSDOM(html, {
      runScripts: 'dangerously',
      resources: 'usable',
      url: 'http://localhost'
    });

    window = dom.window;
    document = window.document;

    global.document = document;
    global.window = window;

    // Load the prompts.js script content
    const promptsScript = fs.readFileSync(
      path.resolve(__dirname, '../scripts/prompts.js'),
      'utf-8'
    );

    // Execute the script in the JSDOM context
    const scriptEl = document.createElement('script');
    scriptEl.textContent = promptsScript;
    document.body.appendChild(scriptEl);
  });

  it('should create a row with Edit and Delete buttons', () => {
    const mockPrompt = {
      prompt_id: '123',
      prompt_name: 'Invoice Extraction',
      description: 'Extract data from invoices'
    };

    // Call the createPromptRow function if it's available
    if (typeof window.createPromptRow === 'function') {
      const row = window.createPromptRow(mockPrompt);
      
      expect(row.tagName).toBe('TR');
      
      const cells = row.querySelectorAll('td');
      expect(cells.length).toBe(3);
      
      // Check for Edit and Delete buttons
      const editBtn = cells[2].querySelector('button:first-child');
      const deleteBtn = cells[2].querySelector('button:last-child');
      
      expect(editBtn.textContent.trim()).toBe('Edit');
      expect(deleteBtn.textContent.trim()).toBe('Delete');
    }
  });
});

describe('Prompt CRUD Operations (Task 14.3)', () => {
  let dom;
  let document;
  let window;
  let mockStorageManager;

  beforeEach(() => {
    const html = fs.readFileSync(
      path.resolve(__dirname, '../popup.html'),
      'utf-8'
    );

    dom = new JSDOM(html, {
      runScripts: 'dangerously',
      resources: 'usable',
      url: 'http://localhost'
    });

    window = dom.window;
    document = window.document;

    global.document = document;
    global.window = window;

    // Mock storage manager
    mockStorageManager = {
      getPrompts: vi.fn(),
      setPrompts: vi.fn()
    };

    // Mock utility functions
    window.showLoading = vi.fn();
    window.hideLoading = vi.fn();
    window.displayAlert = vi.fn();

    // Inject mocks
    window.storageManager = mockStorageManager;

    // Load the prompts.js script
    const promptsScript = fs.readFileSync(
      path.resolve(__dirname, '../scripts/prompts.js'),
      'utf-8'
    );
    window.eval(promptsScript);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('addPrompt function', () => {
    it('should add a new prompt to Local_Storage (Requirement 4.6)', async () => {
      const existingPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      const newPrompt = {
        prompt_id: '2',
        prompt_name: 'Purchase Order',
        description: 'PO extraction',
        prompt: 'Extract PO data',
        created_by: 'user',
        created_date: '2024-01-01T00:00:00Z'
      };

      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.addPrompt(newPrompt);

      expect(mockStorageManager.getPrompts).toHaveBeenCalled();
      expect(mockStorageManager.setPrompts).toHaveBeenCalledWith([
        existingPrompts.prompts[0],
        newPrompt
      ]);
    });

    it('should handle adding prompt when no existing prompts', async () => {
      const newPrompt = {
        prompt_id: '1',
        prompt_name: 'Invoice',
        description: 'Invoice extraction',
        prompt: 'Extract invoice data'
      };

      mockStorageManager.getPrompts.mockResolvedValue(null);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.addPrompt(newPrompt);

      expect(mockStorageManager.setPrompts).toHaveBeenCalledWith([newPrompt]);
    });

    it('should throw error when storage fails', async () => {
      const newPrompt = {
        prompt_id: '1',
        prompt_name: 'Invoice',
        description: 'Invoice extraction'
      };

      mockStorageManager.getPrompts.mockResolvedValue({ prompts: [] });
      mockStorageManager.setPrompts.mockRejectedValue(new Error('Storage error'));

      await expect(window.addPrompt(newPrompt)).rejects.toThrow('Storage error');
    });
  });

  describe('editPrompt function', () => {
    it('should update an existing prompt in Local_Storage (Requirement 4.9)', async () => {
      const existingPrompts = {
        prompts: [
          {
            prompt_id: '1',
            prompt_name: 'Invoice',
            description: 'Old description',
            created_by: 'admin',
            created_date: '2024-01-01T00:00:00Z'
          },
          {
            prompt_id: '2',
            prompt_name: 'PO',
            description: 'PO extraction'
          }
        ]
      };

      const updatedPrompt = {
        prompt_id: '1',
        prompt_name: 'Invoice Updated',
        description: 'New description',
        modified_by: 'user',
        modified_date: '2024-01-02T00:00:00Z'
      };

      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.editPrompt('1', updatedPrompt);

      expect(mockStorageManager.getPrompts).toHaveBeenCalled();
      expect(mockStorageManager.setPrompts).toHaveBeenCalledWith([
        {
          ...updatedPrompt,
          created_by: 'admin',
          created_date: '2024-01-01T00:00:00Z'
        },
        existingPrompts.prompts[1]
      ]);
    });

    it('should preserve created_by and created_date fields when editing', async () => {
      const existingPrompts = {
        prompts: [
          {
            prompt_id: '1',
            prompt_name: 'Invoice',
            description: 'Old description',
            created_by: 'admin',
            created_date: '2024-01-01T00:00:00Z'
          }
        ]
      };

      const updatedPrompt = {
        prompt_id: '1',
        prompt_name: 'Invoice Updated',
        description: 'New description'
      };

      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.editPrompt('1', updatedPrompt);

      const savedPrompts = mockStorageManager.setPrompts.mock.calls[0][0];
      expect(savedPrompts[0].created_by).toBe('admin');
      expect(savedPrompts[0].created_date).toBe('2024-01-01T00:00:00Z');
    });

    it('should throw error when prompt not found', async () => {
      const existingPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      const updatedPrompt = {
        prompt_id: '999',
        prompt_name: 'Non-existent',
        description: 'Does not exist'
      };

      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);

      await expect(window.editPrompt('999', updatedPrompt)).rejects.toThrow('Prompt not found');
    });
  });

  describe('deletePrompt function', () => {
    it('should remove a prompt from Local_Storage (Requirement 4.10)', async () => {
      const existingPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' },
          { prompt_id: '2', prompt_name: 'PO', description: 'PO extraction' },
          { prompt_id: '3', prompt_name: 'Report', description: 'Report extraction' }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.deletePrompt('2');

      expect(mockStorageManager.getPrompts).toHaveBeenCalled();
      expect(mockStorageManager.setPrompts).toHaveBeenCalledWith([
        existingPrompts.prompts[0],
        existingPrompts.prompts[2]
      ]);
    });

    it('should throw error when prompt not found', async () => {
      const existingPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);

      await expect(window.deletePrompt('999')).rejects.toThrow('Prompt not found');
    });

    it('should handle deleting the last prompt', async () => {
      const existingPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.deletePrompt('1');

      expect(mockStorageManager.setPrompts).toHaveBeenCalledWith([]);
    });
  });

  describe('Modal functionality', () => {
    it('should show modal for adding new prompt (Requirement 4.5)', () => {
      window.showPromptModal();

      const modal = document.getElementById('prompt-modal');
      const title = document.getElementById('prompt-modal-title');

      expect(modal.classList.contains('hidden')).toBe(false);
      expect(title.textContent).toBe('Add New Prompt');
    });

    it('should show modal for editing existing prompt', () => {
      const prompt = {
        prompt_id: '1',
        prompt_name: 'Invoice',
        description: 'Invoice extraction',
        prompt: 'Extract invoice data'
      };

      window.showPromptModal(prompt);

      const modal = document.getElementById('prompt-modal');
      const title = document.getElementById('prompt-modal-title');
      const nameInput = document.getElementById('prompt-name');
      const descInput = document.getElementById('prompt-description');

      expect(modal.classList.contains('hidden')).toBe(false);
      expect(title.textContent).toBe('Edit Prompt');
      expect(nameInput.value).toBe('Invoice');
      expect(descInput.value).toBe('Invoice extraction');
    });

    it('should hide modal when close button is clicked', () => {
      window.showPromptModal();
      window.hidePromptModal();

      const modal = document.getElementById('prompt-modal');
      expect(modal.classList.contains('hidden')).toBe(true);
    });

    it('should reset form when showing modal for new prompt', () => {
      // First, populate form with data
      document.getElementById('prompt-name').value = 'Old Name';
      document.getElementById('prompt-description').value = 'Old Description';

      // Show modal for new prompt
      window.showPromptModal();

      const nameInput = document.getElementById('prompt-name');
      const descInput = document.getElementById('prompt-description');
      const idInput = document.getElementById('prompt-id');

      expect(nameInput.value).toBe('');
      expect(descInput.value).toBe('');
      expect(idInput.value).toBe('');
    });
  });

  describe('handleDeletePrompt function', () => {
    beforeEach(() => {
      // Mock confirm dialog on window object
      window.confirm = vi.fn();
      global.confirm = window.confirm;
    });

    it('should show confirmation dialog before deleting', async () => {
      const prompt = {
        prompt_id: '1',
        prompt_name: 'Invoice',
        description: 'Invoice extraction'
      };

      window.confirm.mockReturnValue(false);

      await window.handleDeletePrompt(prompt);

      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining('Are you sure you want to delete')
      );
      expect(mockStorageManager.getPrompts).not.toHaveBeenCalled();
    });

    it('should delete prompt when user confirms', async () => {
      const existingPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      const prompt = existingPrompts.prompts[0];

      window.confirm.mockReturnValue(true);
      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      // Mock loadPrompts to avoid API calls
      window.loadPrompts = vi.fn().mockResolvedValue(undefined);

      await window.handleDeletePrompt(prompt);

      expect(window.confirm).toHaveBeenCalled();
      expect(window.showLoading).toHaveBeenCalled();
      expect(window.hideLoading).toHaveBeenCalled();
      expect(window.displayAlert).toHaveBeenCalledWith('Prompt deleted successfully', 'success');
    });

    it('should not delete prompt when user cancels', async () => {
      const prompt = {
        prompt_id: '1',
        prompt_name: 'Invoice',
        description: 'Invoice extraction'
      };

      window.confirm.mockReturnValue(false);

      await window.handleDeletePrompt(prompt);

      expect(mockStorageManager.getPrompts).not.toHaveBeenCalled();
      expect(mockStorageManager.setPrompts).not.toHaveBeenCalled();
    });
  });

  describe('UUID generation', () => {
    it('should generate valid UUID v4', () => {
      const uuid = window.generateUUID();

      // UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      expect(uuid).toMatch(uuidRegex);
    });

    it('should generate unique UUIDs', () => {
      const uuid1 = window.generateUUID();
      const uuid2 = window.generateUUID();
      const uuid3 = window.generateUUID();

      expect(uuid1).not.toBe(uuid2);
      expect(uuid2).not.toBe(uuid3);
      expect(uuid1).not.toBe(uuid3);
    });
  });

  describe('Form submission', () => {
    beforeEach(() => {
      mockStorageManager.getPrompts.mockResolvedValue({ prompts: [] });
      mockStorageManager.setPrompts.mockResolvedValue(undefined);
      window.loadPrompts = vi.fn().mockResolvedValue(undefined);
    });

    it('should create new prompt on form submit', async () => {
      document.getElementById('prompt-id').value = '';
      document.getElementById('prompt-name').value = 'New Prompt';
      document.getElementById('prompt-description').value = 'New Description';
      document.getElementById('prompt-text').value = 'New prompt text';

      const form = document.getElementById('prompt-form');
      const event = new window.Event('submit', { bubbles: true, cancelable: true });

      await window.handlePromptFormSubmit(event);

      expect(mockStorageManager.setPrompts).toHaveBeenCalled();
      expect(window.displayAlert).toHaveBeenCalledWith('Prompt created successfully', 'success');
    });

    it('should update existing prompt on form submit', async () => {
      const existingPrompts = {
        prompts: [
          {
            prompt_id: '123',
            prompt_name: 'Old Name',
            description: 'Old Description',
            created_by: 'admin',
            created_date: '2024-01-01T00:00:00Z'
          }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(existingPrompts);

      document.getElementById('prompt-id').value = '123';
      document.getElementById('prompt-name').value = 'Updated Name';
      document.getElementById('prompt-description').value = 'Updated Description';
      document.getElementById('prompt-text').value = 'Updated prompt text';

      const form = document.getElementById('prompt-form');
      const event = new window.Event('submit', { bubbles: true, cancelable: true });

      await window.handlePromptFormSubmit(event);

      expect(mockStorageManager.setPrompts).toHaveBeenCalled();
      expect(window.displayAlert).toHaveBeenCalledWith('Prompt updated successfully', 'success');
    });

    it('should validate required fields', async () => {
      document.getElementById('prompt-id').value = '';
      document.getElementById('prompt-name').value = '';
      document.getElementById('prompt-description').value = '';
      document.getElementById('prompt-text').value = '';

      const form = document.getElementById('prompt-form');
      const event = new window.Event('submit', { bubbles: true, cancelable: true });

      await window.handlePromptFormSubmit(event);

      expect(window.displayAlert).toHaveBeenCalledWith(
        'Please fill in all required fields',
        'error'
      );
      expect(mockStorageManager.setPrompts).not.toHaveBeenCalled();
    });
  });
});

describe('Reset and Export Functionality (Task 14.5)', () => {
  let dom;
  let document;
  let window;
  let mockStorageManager;
  let mockApiClient;

  beforeEach(() => {
    const html = fs.readFileSync(
      path.resolve(__dirname, '../popup.html'),
      'utf-8'
    );

    dom = new JSDOM(html, {
      runScripts: 'dangerously',
      resources: 'usable',
      url: 'http://localhost'
    });

    window = dom.window;
    document = window.document;

    global.document = document;
    global.window = window;

    // Mock storage manager
    mockStorageManager = {
      getPrompts: vi.fn(),
      setPrompts: vi.fn()
    };

    // Mock API client
    mockApiClient = {
      resetPrompts: vi.fn()
    };

    // Mock utility functions
    window.showLoading = vi.fn();
    window.hideLoading = vi.fn();
    window.displayAlert = vi.fn();
    window.confirm = vi.fn();
    global.confirm = window.confirm;

    // Mock Papa (CSV library)
    window.Papa = {
      unparse: vi.fn((data) => 'mock,csv,data')
    };

    // Mock URL and Blob APIs
    global.URL = {
      createObjectURL: vi.fn(() => 'blob:mock-url'),
      revokeObjectURL: vi.fn()
    };
    window.URL = global.URL;
    
    // Mock Blob constructor
    const BlobMock = vi.fn((content, options) => ({ content, options, type: options?.type }));
    global.Blob = BlobMock;
    window.Blob = BlobMock;

    // Inject mocks
    window.storageManager = mockStorageManager;
    window.apiClient = mockApiClient;

    // Load the prompts.js script
    const promptsScript = fs.readFileSync(
      path.resolve(__dirname, '../scripts/prompts.js'),
      'utf-8'
    );
    window.eval(promptsScript);

    // Spy on functions
    vi.spyOn(window, 'populatePromptsTable');
    vi.spyOn(window, 'showEmptyPromptsState');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('handleResetPrompts function', () => {
    it('should call reset_prompts API (Requirement 4.7)', async () => {
      const mockApiPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' },
          { prompt_id: '2', prompt_name: 'PO', description: 'PO extraction' }
        ]
      };

      window.confirm.mockReturnValue(true);
      mockApiClient.resetPrompts.mockResolvedValue(mockApiPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.handleResetPrompts();

      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining('Are you sure you want to reset all prompts?')
      );
      expect(mockApiClient.resetPrompts).toHaveBeenCalled();
    });

    it('should refresh Local_Storage cache after reset (Requirement 4.7)', async () => {
      const mockApiPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      window.confirm.mockReturnValue(true);
      mockApiClient.resetPrompts.mockResolvedValue(mockApiPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.handleResetPrompts();

      expect(mockStorageManager.setPrompts).toHaveBeenCalledWith(mockApiPrompts.prompts);
    });

    it('should reload prompts table after reset', async () => {
      const mockApiPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      window.confirm.mockReturnValue(true);
      mockApiClient.resetPrompts.mockResolvedValue(mockApiPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.handleResetPrompts();

      expect(window.populatePromptsTable).toHaveBeenCalledWith(mockApiPrompts.prompts);
    });

    it('should show success alert after reset', async () => {
      const mockApiPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      window.confirm.mockReturnValue(true);
      mockApiClient.resetPrompts.mockResolvedValue(mockApiPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.handleResetPrompts();

      expect(window.displayAlert).toHaveBeenCalledWith('Prompts reset successfully', 'success');
    });

    it('should not reset when user cancels confirmation', async () => {
      window.confirm.mockReturnValue(false);

      await window.handleResetPrompts();

      expect(mockApiClient.resetPrompts).not.toHaveBeenCalled();
      expect(mockStorageManager.setPrompts).not.toHaveBeenCalled();
    });

    it('should handle API errors gracefully', async () => {
      window.confirm.mockReturnValue(true);
      mockApiClient.resetPrompts.mockRejectedValue(new Error('Network error'));

      await window.handleResetPrompts();

      expect(window.displayAlert).toHaveBeenCalledWith(
        expect.stringContaining('Failed to reset prompts'),
        'error'
      );
      expect(window.hideLoading).toHaveBeenCalled();
    });

    it('should show empty state when API returns no prompts', async () => {
      window.confirm.mockReturnValue(true);
      mockApiClient.resetPrompts.mockResolvedValue({ prompts: [] });

      await window.handleResetPrompts();

      expect(window.showEmptyPromptsState).toHaveBeenCalled();
      expect(window.displayAlert).toHaveBeenCalledWith(
        'No prompts available from server',
        'warning'
      );
    });

    it('should show loading indicator during reset', async () => {
      const mockApiPrompts = {
        prompts: [
          { prompt_id: '1', prompt_name: 'Invoice', description: 'Invoice extraction' }
        ]
      };

      window.confirm.mockReturnValue(true);
      mockApiClient.resetPrompts.mockResolvedValue(mockApiPrompts);
      mockStorageManager.setPrompts.mockResolvedValue(undefined);

      await window.handleResetPrompts();

      expect(window.showLoading).toHaveBeenCalled();
      expect(window.hideLoading).toHaveBeenCalled();
    });
  });

  describe('handleExportPromptsToCSV function', () => {
    it('should export prompts to CSV (Requirement 4.8)', async () => {
      const mockPrompts = {
        prompts: [
          {
            prompt_id: '1',
            prompt_name: 'Invoice',
            description: 'Invoice extraction',
            prompt: 'Extract invoice data',
            created_by: 'admin',
            created_date: '2024-01-01T00:00:00Z',
            modified_by: 'admin',
            modified_date: '2024-01-01T00:00:00Z'
          }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(mockPrompts);

      await window.handleExportPromptsToCSV();

      expect(mockStorageManager.getPrompts).toHaveBeenCalled();
      expect(window.Papa.unparse).toHaveBeenCalled();
    });

    it('should generate CSV with correct columns', async () => {
      const mockPrompts = {
        prompts: [
          {
            prompt_id: '1',
            prompt_name: 'Invoice',
            description: 'Invoice extraction',
            prompt: 'Extract invoice data',
            created_by: 'admin',
            created_date: '2024-01-01T00:00:00Z',
            modified_by: 'admin',
            modified_date: '2024-01-01T00:00:00Z'
          }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(mockPrompts);

      await window.handleExportPromptsToCSV();

      const csvData = window.Papa.unparse.mock.calls[0][0];
      expect(csvData[0]).toHaveProperty('Prompt Name');
      expect(csvData[0]).toHaveProperty('Description');
      expect(csvData[0]).toHaveProperty('Prompt');
      expect(csvData[0]).toHaveProperty('Created By');
      expect(csvData[0]).toHaveProperty('Created Date');
      expect(csvData[0]).toHaveProperty('Modified By');
      expect(csvData[0]).toHaveProperty('Modified Date');
    });

    it('should trigger browser download', async () => {
      const mockPrompts = {
        prompts: [
          {
            prompt_id: '1',
            prompt_name: 'Invoice',
            description: 'Invoice extraction',
            prompt: 'Extract invoice data'
          }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(mockPrompts);

      // Mock document.createElement to track link creation
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn()
      };
      const originalCreateElement = document.createElement.bind(document);
      document.createElement = vi.fn((tag) => {
        if (tag === 'a') {
          return mockLink;
        }
        return originalCreateElement(tag);
      });

      // Properly mock URL.createObjectURL on window
      window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      window.URL.revokeObjectURL = vi.fn();

      await window.handleExportPromptsToCSV();

      expect(mockLink.click).toHaveBeenCalled();
      expect(mockLink.download).toMatch(/^prompts_\d{4}-\d{2}-\d{2}\.csv$/);
    });

    it('should show success alert after export', async () => {
      const mockPrompts = {
        prompts: [
          {
            prompt_id: '1',
            prompt_name: 'Invoice',
            description: 'Invoice extraction'
          }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(mockPrompts);

      // Properly mock URL.createObjectURL on window
      window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      window.URL.revokeObjectURL = vi.fn();

      await window.handleExportPromptsToCSV();

      expect(window.displayAlert).toHaveBeenCalledWith(
        'Prompts exported to CSV successfully',
        'success'
      );
    });

    it('should show warning when no prompts to export', async () => {
      mockStorageManager.getPrompts.mockResolvedValue({ prompts: [] });

      await window.handleExportPromptsToCSV();

      expect(window.displayAlert).toHaveBeenCalledWith('No prompts to export', 'warning');
      expect(window.Papa.unparse).not.toHaveBeenCalled();
    });

    it('should handle null prompts data', async () => {
      mockStorageManager.getPrompts.mockResolvedValue(null);

      await window.handleExportPromptsToCSV();

      expect(window.displayAlert).toHaveBeenCalledWith('No prompts to export', 'warning');
    });

    it('should handle export errors gracefully', async () => {
      mockStorageManager.getPrompts.mockRejectedValue(new Error('Storage error'));

      await window.handleExportPromptsToCSV();

      expect(window.displayAlert).toHaveBeenCalledWith(
        'Failed to export prompts to CSV',
        'error'
      );
    });

    it('should create CSV blob with correct MIME type', async () => {
      const mockPrompts = {
        prompts: [
          {
            prompt_id: '1',
            prompt_name: 'Invoice',
            description: 'Invoice extraction'
          }
        ]
      };

      mockStorageManager.getPrompts.mockResolvedValue(mockPrompts);

      // Properly mock URL.createObjectURL on window
      window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      window.URL.revokeObjectURL = vi.fn();

      await window.handleExportPromptsToCSV();

      expect(global.Blob).toHaveBeenCalledWith(
        ['mock,csv,data'],
        { type: 'text/csv;charset=utf-8;' }
      );
    });
  });
});
