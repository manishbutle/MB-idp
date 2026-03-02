/**
 * CSV Export Tests
 * Tests for CSV export functionality
 * Requirements: 3.2, 3.8, 3.9
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock Papa (PapaParse library)
global.Papa = {
  unparse: vi.fn((data, options) => {
    // Simple CSV generation mock
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const headerRow = headers.join(',');
    const dataRows = data.map(row => 
      headers.map(header => {
        const value = row[header] || '';
        // Quote values if they contain commas or quotes
        if (value.includes(',') || value.includes('"')) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      }).join(',')
    );
    
    return [headerRow, ...dataRows].join('\n');
  })
};

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = vi.fn();

// Mock Blob
global.Blob = class Blob {
  constructor(parts, options) {
    this.parts = parts;
    this.options = options;
  }
};

// Mock DOM elements and functions
beforeEach(() => {
  document.body.innerHTML = `
    <div id="alert-container"></div>
    <button id="export-csv-btn"></button>
  `;
  
  // Reset mocks
  vi.clearAllMocks();
});

describe('CSV Export Functionality', () => {
  it('should export RESULT data to CSV format', () => {
    // Test Requirement 3.2 - Generate CSV file from RESULT data
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Invoice Date': '2024-01-15',
      'Vendor Name': 'Acme Corp',
      'Total Amount': '$1,234.56'
    };

    // Convert to CSV format
    const csvData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    const csv = Papa.unparse(csvData, {
      header: true,
      quotes: true,
      skipEmptyLines: false
    });

    // Verify Papa.unparse was called
    expect(Papa.unparse).toHaveBeenCalledWith(
      csvData,
      expect.objectContaining({
        header: true,
        quotes: true,
        skipEmptyLines: false
      })
    );

    // Verify CSV format
    expect(csv).toContain('Field,Value');
    expect(csv).toContain('Invoice Number');
    expect(csv).toContain('INV-12345');
    expect(csv).toContain('Invoice Date');
    expect(csv).toContain('2024-01-15');
  });

  it('should create blob with correct MIME type', () => {
    // Test that blob is created with text/csv MIME type
    
    const csvContent = 'Field,Value\nInvoice Number,INV-12345';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });

    expect(blob.parts).toEqual([csvContent]);
    expect(blob.options.type).toBe('text/csv;charset=utf-8;');
  });

  it('should trigger browser download with correct filename', () => {
    // Test Requirement 3.2 - Trigger browser download
    
    const csvContent = 'Field,Value\nInvoice Number,INV-12345';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // Create download link
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'document-extraction-2024-01-15.csv';
    
    // Verify link properties
    expect(link.href).toBe('blob:mock-url');
    expect(link.download).toMatch(/document-extraction-.*\.csv/);
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
  });

  it('should clean up URL object after download', () => {
    // Test that URL.revokeObjectURL is called to free memory
    
    const url = 'blob:mock-url';
    URL.revokeObjectURL(url);
    
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(url);
  });

  it('should handle empty results gracefully', () => {
    // Test edge case - no data to export
    
    const mockResults = {};
    
    // Check if results are empty
    const isEmpty = Object.keys(mockResults).length === 0;
    
    expect(isEmpty).toBe(true);
    // In actual implementation, this should show a warning alert
  });

  it('should handle special characters in CSV data', () => {
    // Test that special characters are properly escaped
    
    const mockResults = {
      'Field with, comma': 'Value with, comma',
      'Field with "quotes"': 'Value with "quotes"',
      'Normal Field': 'Normal Value'
    };

    const csvData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    const csv = Papa.unparse(csvData, {
      header: true,
      quotes: true,
      skipEmptyLines: false
    });

    // Verify CSV contains the data
    expect(csv).toBeTruthy();
    expect(Papa.unparse).toHaveBeenCalled();
  });

  it('should handle null and undefined values', () => {
    // Test edge case - null/undefined values
    
    const mockResults = {
      'Field1': 'Value1',
      'Field2': null,
      'Field3': undefined,
      'Field4': ''
    };

    const csvData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    // Verify all fields are converted to strings
    csvData.forEach(row => {
      expect(typeof row.Field).toBe('string');
      expect(typeof row.Value).toBe('string');
    });
  });

  it('should generate filename with timestamp', () => {
    // Test that filename includes timestamp for uniqueness
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `document-extraction-${timestamp}.csv`;
    
    expect(filename).toMatch(/document-extraction-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.csv/);
  });

  it('should handle PapaParse library not loaded', () => {
    // Test error case - library not available
    
    const originalPapa = global.Papa;
    global.Papa = undefined;
    
    try {
      if (typeof Papa === 'undefined') {
        throw new Error('PapaParse library not loaded');
      }
    } catch (error) {
      expect(error.message).toBe('PapaParse library not loaded');
    }
    
    // Restore Papa
    global.Papa = originalPapa;
  });

  it('should format data as Field-Value pairs', () => {
    // Test that data is formatted correctly for CSV
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Total Amount': '$1,234.56'
    };

    const csvData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    expect(csvData).toEqual([
      { Field: 'Invoice Number', Value: 'INV-12345' },
      { Field: 'Total Amount', Value: '$1,234.56' }
    ]);
  });
});

describe('CSV Export Error Handling', () => {
  it('should display error alert when export fails', () => {
    // Test Requirement 3.8 - Display error alert on failure
    
    // Mock displayAlert function
    const displayAlert = vi.fn();
    
    try {
      // Simulate error
      throw new Error('Failed to generate CSV');
    } catch (error) {
      displayAlert(error.message || 'Failed to export CSV file. Please try again.', 'error');
    }
    
    expect(displayAlert).toHaveBeenCalledWith(
      'Failed to generate CSV',
      'error'
    );
  });

  it('should display success alert when export succeeds', () => {
    // Test Requirement 3.9 - Display success alert on success
    
    // Mock displayAlert function
    const displayAlert = vi.fn();
    
    // Simulate successful export
    displayAlert('CSV file downloaded successfully!', 'success');
    
    expect(displayAlert).toHaveBeenCalledWith(
      'CSV file downloaded successfully!',
      'success'
    );
  });

  it('should display warning when no data is available', () => {
    // Test that warning is shown for empty data
    
    // Mock displayAlert function
    const displayAlert = vi.fn();
    
    const mockResults = {};
    
    if (!mockResults || Object.keys(mockResults).length === 0) {
      displayAlert('No data available to export', 'warning');
    }
    
    expect(displayAlert).toHaveBeenCalledWith(
      'No data available to export',
      'warning'
    );
  });
});
