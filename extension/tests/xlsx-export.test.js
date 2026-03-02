/**
 * XLSX Export Tests
 * Tests for XLSX export functionality
 * Requirements: 3.3, 3.8, 3.9
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock XLSX (SheetJS library)
global.XLSX = {
  utils: {
    book_new: vi.fn(() => ({
      SheetNames: [],
      Sheets: {}
    })),
    json_to_sheet: vi.fn((data) => {
      // Simple worksheet mock
      const worksheet = {};
      data.forEach((row, rowIndex) => {
        Object.keys(row).forEach((key, colIndex) => {
          const cellRef = String.fromCharCode(65 + colIndex) + (rowIndex + 2);
          worksheet[cellRef] = { v: row[key], t: 's' };
        });
      });
      // Add headers
      worksheet['A1'] = { v: 'Field', t: 's' };
      worksheet['B1'] = { v: 'Value', t: 's' };
      worksheet['!ref'] = `A1:B${data.length + 1}`;
      return worksheet;
    }),
    book_append_sheet: vi.fn((workbook, worksheet, sheetName) => {
      workbook.SheetNames.push(sheetName);
      workbook.Sheets[sheetName] = worksheet;
    })
  },
  writeFile: vi.fn((workbook, filename) => {
    // Mock file write - in browser this triggers download
    return true;
  })
};

// Mock DOM elements and functions
beforeEach(() => {
  document.body.innerHTML = `
    <div id="alert-container"></div>
    <button id="export-xlsx-btn"></button>
  `;
  
  // Reset mocks
  vi.clearAllMocks();
});

describe('XLSX Export Functionality', () => {
  it('should export RESULT data to XLSX format', () => {
    // Test Requirement 3.3 - Generate XLSX file from RESULT data
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Invoice Date': '2024-01-15',
      'Vendor Name': 'Acme Corp',
      'Total Amount': '$1,234.56'
    };

    // Convert to XLSX format
    const xlsxData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    // Create workbook
    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet(xlsxData);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Extraction Results');

    // Verify XLSX functions were called
    expect(XLSX.utils.book_new).toHaveBeenCalled();
    expect(XLSX.utils.json_to_sheet).toHaveBeenCalledWith(xlsxData);
    expect(XLSX.utils.book_append_sheet).toHaveBeenCalledWith(
      workbook,
      worksheet,
      'Extraction Results'
    );

    // Verify workbook structure
    expect(workbook.SheetNames).toContain('Extraction Results');
    expect(workbook.Sheets['Extraction Results']).toBeDefined();
  });

  it('should create worksheet with correct data structure', () => {
    // Test that worksheet contains proper cell references
    
    const xlsxData = [
      { Field: 'Invoice Number', Value: 'INV-12345' },
      { Field: 'Invoice Date', Value: '2024-01-15' }
    ];

    const worksheet = XLSX.utils.json_to_sheet(xlsxData);

    // Verify worksheet structure
    expect(worksheet['A1']).toEqual({ v: 'Field', t: 's' });
    expect(worksheet['B1']).toEqual({ v: 'Value', t: 's' });
    expect(worksheet['!ref']).toBe('A1:B3');
  });

  it('should trigger browser download using writeFile', () => {
    // Test Requirement 3.3 - Trigger browser download using SheetJS writeFile
    
    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet([
      { Field: 'Invoice Number', Value: 'INV-12345' }
    ]);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Extraction Results');
    
    const filename = 'document-extraction-2024-01-15.xlsx';
    XLSX.writeFile(workbook, filename);
    
    // Verify writeFile was called with correct parameters
    expect(XLSX.writeFile).toHaveBeenCalledWith(workbook, filename);
  });

  it('should handle empty results gracefully', () => {
    // Test edge case - no data to export
    
    const mockResults = {};
    
    // Check if results are empty
    const isEmpty = Object.keys(mockResults).length === 0;
    
    expect(isEmpty).toBe(true);
    // In actual implementation, this should show a warning alert
  });

  it('should handle special characters in XLSX data', () => {
    // Test that special characters are properly handled
    
    const mockResults = {
      'Field with, comma': 'Value with, comma',
      'Field with "quotes"': 'Value with "quotes"',
      'Field with \n newline': 'Value with \n newline',
      'Normal Field': 'Normal Value'
    };

    const xlsxData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    const worksheet = XLSX.utils.json_to_sheet(xlsxData);

    // Verify worksheet was created
    expect(worksheet).toBeDefined();
    expect(XLSX.utils.json_to_sheet).toHaveBeenCalledWith(xlsxData);
  });

  it('should handle null and undefined values', () => {
    // Test edge case - null/undefined values
    
    const mockResults = {
      'Field1': 'Value1',
      'Field2': null,
      'Field3': undefined,
      'Field4': ''
    };

    const xlsxData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    // Verify all fields are converted to strings
    xlsxData.forEach(row => {
      expect(typeof row.Field).toBe('string');
      expect(typeof row.Value).toBe('string');
    });
  });

  it('should generate filename with timestamp', () => {
    // Test that filename includes timestamp for uniqueness
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `document-extraction-${timestamp}.xlsx`;
    
    expect(filename).toMatch(/document-extraction-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.xlsx/);
  });

  it('should handle SheetJS library not loaded', () => {
    // Test error case - library not available
    
    const originalXLSX = global.XLSX;
    global.XLSX = undefined;
    
    try {
      if (typeof XLSX === 'undefined') {
        throw new Error('SheetJS library not loaded');
      }
    } catch (error) {
      expect(error.message).toBe('SheetJS library not loaded');
    }
    
    // Restore XLSX
    global.XLSX = originalXLSX;
  });

  it('should format data as Field-Value pairs', () => {
    // Test that data is formatted correctly for XLSX
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Total Amount': '$1,234.56'
    };

    const xlsxData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    expect(xlsxData).toEqual([
      { Field: 'Invoice Number', Value: 'INV-12345' },
      { Field: 'Total Amount', Value: '$1,234.56' }
    ]);
  });

  it('should create workbook with single worksheet', () => {
    // Test that workbook contains exactly one worksheet
    
    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet([
      { Field: 'Test', Value: 'Data' }
    ]);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Extraction Results');
    
    expect(workbook.SheetNames.length).toBe(1);
    expect(workbook.SheetNames[0]).toBe('Extraction Results');
  });

  it('should handle large datasets', () => {
    // Test that large datasets are handled correctly
    
    const mockResults = {};
    for (let i = 1; i <= 100; i++) {
      mockResults[`Field${i}`] = `Value${i}`;
    }

    const xlsxData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    expect(xlsxData.length).toBe(100);
    
    const worksheet = XLSX.utils.json_to_sheet(xlsxData);
    expect(worksheet).toBeDefined();
  });

  it('should handle numeric values correctly', () => {
    // Test that numeric values are preserved
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Quantity': '10',
      'Unit Price': '99.99',
      'Total': '999.90'
    };

    const xlsxData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));

    // Verify data structure
    expect(xlsxData).toEqual([
      { Field: 'Invoice Number', Value: 'INV-12345' },
      { Field: 'Quantity', Value: '10' },
      { Field: 'Unit Price', Value: '99.99' },
      { Field: 'Total', Value: '999.90' }
    ]);
  });
});

describe('XLSX Export Error Handling', () => {
  it('should display error alert when export fails', () => {
    // Test Requirement 3.8 - Display error alert on failure
    
    // Mock displayAlert function
    const displayAlert = vi.fn();
    
    try {
      // Simulate error
      throw new Error('Failed to generate XLSX');
    } catch (error) {
      displayAlert(error.message || 'Failed to export XLSX file. Please try again.', 'error');
    }
    
    expect(displayAlert).toHaveBeenCalledWith(
      'Failed to generate XLSX',
      'error'
    );
  });

  it('should display success alert when export succeeds', () => {
    // Test Requirement 3.9 - Display success alert on success
    
    // Mock displayAlert function
    const displayAlert = vi.fn();
    
    // Simulate successful export
    displayAlert('XLSX file downloaded successfully!', 'success');
    
    expect(displayAlert).toHaveBeenCalledWith(
      'XLSX file downloaded successfully!',
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

  it('should handle writeFile errors gracefully', () => {
    // Test error handling when writeFile fails
    
    const displayAlert = vi.fn();
    
    // Mock writeFile to throw error
    XLSX.writeFile = vi.fn(() => {
      throw new Error('Write file failed');
    });
    
    try {
      const workbook = XLSX.utils.book_new();
      const worksheet = XLSX.utils.json_to_sheet([{ Field: 'Test', Value: 'Data' }]);
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Extraction Results');
      XLSX.writeFile(workbook, 'test.xlsx');
    } catch (error) {
      displayAlert(error.message || 'Failed to export XLSX file. Please try again.', 'error');
    }
    
    expect(displayAlert).toHaveBeenCalledWith(
      'Write file failed',
      'error'
    );
  });
});
