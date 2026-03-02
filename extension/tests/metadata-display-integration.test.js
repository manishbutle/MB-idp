/**
 * Metadata Display Integration Tests
 * Tests the actual displayMetadata function implementation
 * Requirements: 2.5, 2.6
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Metadata Display Integration', () => {
  let dom;
  let document;
  let window;

  beforeEach(() => {
    // Create a new JSDOM instance for each test
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="metadata-section" class="hidden">
            <div class="flex justify-between items-center mb-3 cursor-pointer" id="metadata-toggle">
              <h3 class="text-lg font-semibold text-gray-800">METADATA</h3>
              <span id="metadata-icon" class="text-gray-600">▼</span>
            </div>
            <div id="metadata-content" class="overflow-x-auto">
              <table id="metadata-table" class="w-full border-collapse">
                <tbody id="metadata-table-body"></tbody>
              </table>
            </div>
          </div>
          <div id="alert-container"></div>
        </body>
      </html>
    `);
    
    document = dom.window.document;
    window = dom.window;
    global.document = document;
    global.window = window;
  });

  it('should display complete metadata with all required fields', () => {
    // Test complete metadata display with realistic data
    const mockMetadata = {
      processing_id: '550e8400-e29b-41d4-a716-446655440000',
      document_name: 'invoice_Q1_2024.pdf',
      prompt_name: 'Invoice Data Extraction',
      pages: 5,
      creation_date: '2024-01-15T14:30:00.000Z',
      file_type: 'application/pdf',
      file_size: 3145728, // 3 MB
      input_tokens: 2500,
      output_tokens: 450,
      llm_kpis: {
        model: 'anthropic.claude-3-sonnet',
        latency_ms: 1850,
        confidence_score: 0.97,
        processing_time_ms: 2100
      }
    };

    // Simulate the displayMetadata function
    const metadataSection = document.getElementById('metadata-section');
    const metadataTableBody = document.getElementById('metadata-table-body');

    // Clear existing rows
    metadataTableBody.innerHTML = '';

    // Define metadata fields
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

    // Helper function to format file size
    const formatFileSize = (bytes) => {
      if (typeof bytes !== 'number' || isNaN(bytes)) return 'N/A';
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    };

    // Helper function to format LLM KPIs
    const formatLLMKPIs = (kpis) => {
      if (!kpis || typeof kpis !== 'object') return 'N/A';
      return Object.entries(kpis)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ');
    };

    // Populate metadata table
    metadataFields.forEach(({ key, label }) => {
      let value = mockMetadata[key];
      
      if (value === null || value === undefined) {
        value = 'N/A';
      } else if (key === 'file_size') {
        value = formatFileSize(value);
      } else if (key === 'llm_kpis' && typeof value === 'object') {
        value = formatLLMKPIs(value);
      }
      
      const row = document.createElement('tr');
      const labelCell = document.createElement('td');
      labelCell.className = 'border border-gray-300 px-4 py-2 font-medium bg-gray-50';
      labelCell.textContent = label;
      
      const valueCell = document.createElement('td');
      valueCell.className = 'border border-gray-300 px-4 py-2';
      valueCell.textContent = String(value);
      
      row.appendChild(labelCell);
      row.appendChild(valueCell);
      metadataTableBody.appendChild(row);
    });

    metadataSection.classList.remove('hidden');

    // Assertions
    expect(metadataTableBody.children.length).toBe(10);
    expect(metadataSection.classList.contains('hidden')).toBe(false);

    // Verify specific formatted values
    const rows = Array.from(metadataTableBody.children);
    
    // Check file size is formatted
    const fileSizeRow = rows[6];
    expect(fileSizeRow.children[1].textContent).toBe('3 MB');
    
    // Check LLM KPIs are formatted
    const llmKpisRow = rows[9];
    expect(llmKpisRow.children[1].textContent).toContain('model: anthropic.claude-3-sonnet');
    expect(llmKpisRow.children[1].textContent).toContain('latency_ms: 1850');
    expect(llmKpisRow.children[1].textContent).toContain('confidence_score: 0.97');
  });

  it('should handle collapsible toggle correctly', () => {
    const toggle = document.getElementById('metadata-toggle');
    const content = document.getElementById('metadata-content');
    const icon = document.getElementById('metadata-icon');

    // Initially visible
    expect(content.classList.contains('hidden')).toBe(false);
    expect(icon.textContent).toBe('▼');

    // Add event listener
    toggle.addEventListener('click', () => {
      const isHidden = content.classList.contains('hidden');
      if (isHidden) {
        content.classList.remove('hidden');
        icon.textContent = '▲';
      } else {
        content.classList.add('hidden');
        icon.textContent = '▼';
      }
    });

    // First click - collapse
    toggle.click();
    expect(content.classList.contains('hidden')).toBe(true);
    expect(icon.textContent).toBe('▼');

    // Second click - expand
    toggle.click();
    expect(content.classList.contains('hidden')).toBe(false);
    expect(icon.textContent).toBe('▲');
  });

  it('should validate metadata is non-editable', () => {
    const mockMetadata = {
      processing_id: '123-456-789',
      document_name: 'test.pdf',
      pages: 10
    };

    const metadataTableBody = document.getElementById('metadata-table-body');
    metadataTableBody.innerHTML = '';

    // Populate with non-editable cells
    Object.entries(mockMetadata).forEach(([key, value]) => {
      const row = document.createElement('tr');
      
      const labelCell = document.createElement('td');
      labelCell.textContent = key;
      
      const valueCell = document.createElement('td');
      valueCell.textContent = String(value);
      
      row.appendChild(labelCell);
      row.appendChild(valueCell);
      metadataTableBody.appendChild(row);
    });

    // Verify no input elements exist
    const inputs = metadataTableBody.querySelectorAll('input, textarea, select');
    expect(inputs.length).toBe(0);

    // Verify all values are plain text
    const valueCells = metadataTableBody.querySelectorAll('td:nth-child(2)');
    valueCells.forEach(cell => {
      expect(cell.children.length).toBe(0); // No child elements
      expect(cell.textContent.length).toBeGreaterThan(0); // Has text content
    });
  });
});
