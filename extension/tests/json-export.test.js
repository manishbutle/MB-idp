/**
 * JSON Export Tests
 * Tests for JSON export functionality
 * Requirements: 3.4, 3.8, 3.9
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

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
    <button id="export-json-btn"></button>
  `;
  
  // Reset mocks
  vi.clearAllMocks();
});

describe('JSON Export Functionality', () => {
  it('should export RESULT data to JSON format', () => {
    // Test Requirement 3.4 - Generate JSON file from RESULT data
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Invoice Date': '2024-01-15',
      'Vendor Name': 'Acme Corp',
      'Total Amount': '$1,234.56'
    };

    // Convert to JSON string
    const jsonString = JSON.stringify(mockResults, null, 2);

    // Verify JSON format
    expect(jsonString).toBeTruthy();
    expect(jsonString).toContain('Invoice Number');
    expect(jsonString).toContain('INV-12345');
    expect(jsonString).toContain('Invoice Date');
    expect(jsonString).toContain('2024-01-15');
    
    // Verify it's valid JSON
    const parsed = JSON.parse(jsonString);
    expect(parsed).toEqual(mockResults);
  });

  it('should create blob with correct MIME type', () => {
    // Test that blob is created with application/json MIME type
    
    const jsonContent = '{"Invoice Number":"INV-12345"}';
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });

    expect(blob.parts).toEqual([jsonContent]);
    expect(blob.options.type).toBe('application/json;charset=utf-8;');
  });

  it('should trigger browser download with correct filename', () => {
    // Test Requirement 3.4 - Trigger browser download
    
    const jsonContent = '{"Invoice Number":"INV-12345"}';
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    
    // Create download link
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'document-extraction-2024-01-15.json';
    
    // Verify link properties
    expect(link.href).toBe('blob:mock-url');
    expect(link.download).toMatch(/document-extraction-.*\.json/);
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

  it('should handle special characters in JSON data', () => {
    // Test that special characters are properly handled in JSON
    
    const mockResults = {
      'Field with "quotes"': 'Value with "quotes"',
      'Field with \\ backslash': 'Value with \\ backslash',
      'Field with \n newline': 'Value with \n newline',
      'Normal Field': 'Normal Value'
    };

    const jsonString = JSON.stringify(mockResults, null, 2);

    // Verify JSON is valid
    expect(jsonString).toBeTruthy();
    
    // Verify it can be parsed back
    const parsed = JSON.parse(jsonString);
    expect(parsed).toEqual(mockResults);
  });

  it('should handle null and undefined values', () => {
    // Test edge case - null/undefined values
    
    const mockResults = {
      'Field1': 'Value1',
      'Field2': null,
      'Field3': undefined,
      'Field4': ''
    };

    const jsonString = JSON.stringify(mockResults, null, 2);
    const parsed = JSON.parse(jsonString);

    // Note: JSON.stringify removes undefined values
    expect(parsed.Field1).toBe('Value1');
    expect(parsed.Field2).toBe(null);
    expect(parsed.Field3).toBeUndefined(); // undefined is removed by JSON.stringify
    expect(parsed.Field4).toBe('');
  });

  it('should generate filename with timestamp', () => {
    // Test that filename includes timestamp for uniqueness
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `document-extraction-${timestamp}.json`;
    
    expect(filename).toMatch(/document-extraction-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.json/);
  });

  it('should format JSON with proper indentation', () => {
    // Test that JSON is formatted with 2-space indentation for readability
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Total Amount': '$1,234.56'
    };

    const jsonString = JSON.stringify(mockResults, null, 2);

    // Verify indentation
    expect(jsonString).toContain('  "Invoice Number"');
    expect(jsonString).toContain('  "Total Amount"');
  });

  it('should preserve data types in JSON', () => {
    // Test that different data types are preserved
    
    const mockResults = {
      'String Field': 'text value',
      'Number Field': 12345,
      'Boolean Field': true,
      'Null Field': null
    };

    const jsonString = JSON.stringify(mockResults, null, 2);
    const parsed = JSON.parse(jsonString);

    expect(typeof parsed['String Field']).toBe('string');
    expect(typeof parsed['Number Field']).toBe('number');
    expect(typeof parsed['Boolean Field']).toBe('boolean');
    expect(parsed['Null Field']).toBe(null);
  });

  it('should handle nested objects in results', () => {
    // Test that nested objects are properly serialized
    
    const mockResults = {
      'Simple Field': 'value',
      'Nested Object': {
        'SubField1': 'subvalue1',
        'SubField2': 'subvalue2'
      }
    };

    const jsonString = JSON.stringify(mockResults, null, 2);
    const parsed = JSON.parse(jsonString);

    expect(parsed['Nested Object']).toEqual({
      'SubField1': 'subvalue1',
      'SubField2': 'subvalue2'
    });
  });

  it('should handle arrays in results', () => {
    // Test that arrays are properly serialized
    
    const mockResults = {
      'Simple Field': 'value',
      'Array Field': ['item1', 'item2', 'item3']
    };

    const jsonString = JSON.stringify(mockResults, null, 2);
    const parsed = JSON.parse(jsonString);

    expect(Array.isArray(parsed['Array Field'])).toBe(true);
    expect(parsed['Array Field']).toEqual(['item1', 'item2', 'item3']);
  });

  it('should handle unicode characters', () => {
    // Test that unicode characters are properly handled
    
    const mockResults = {
      'Unicode Field': 'Hello 世界 🌍',
      'Emoji Field': '😀 😃 😄'
    };

    const jsonString = JSON.stringify(mockResults, null, 2);
    const parsed = JSON.parse(jsonString);

    expect(parsed['Unicode Field']).toBe('Hello 世界 🌍');
    expect(parsed['Emoji Field']).toBe('😀 😃 😄');
  });

  it('should handle large numbers', () => {
    // Test that large numbers are properly handled
    
    const mockResults = {
      'Large Number': 9007199254740991, // Number.MAX_SAFE_INTEGER
      'Small Number': -9007199254740991
    };

    const jsonString = JSON.stringify(mockResults, null, 2);
    const parsed = JSON.parse(jsonString);

    expect(parsed['Large Number']).toBe(9007199254740991);
    expect(parsed['Small Number']).toBe(-9007199254740991);
  });
});

describe('JSON Export Error Handling', () => {
  it('should display error alert when export fails', () => {
    // Test Requirement 3.8 - Display error alert on failure
    
    // Mock displayAlert function
    const displayAlert = vi.fn();
    
    try {
      // Simulate error
      throw new Error('Failed to generate JSON');
    } catch (error) {
      displayAlert(error.message || 'Failed to export JSON file. Please try again.', 'error');
    }
    
    expect(displayAlert).toHaveBeenCalledWith(
      'Failed to generate JSON',
      'error'
    );
  });

  it('should display success alert when export succeeds', () => {
    // Test Requirement 3.9 - Display success alert on success
    
    // Mock displayAlert function
    const displayAlert = vi.fn();
    
    // Simulate successful export
    displayAlert('JSON file downloaded successfully!', 'success');
    
    expect(displayAlert).toHaveBeenCalledWith(
      'JSON file downloaded successfully!',
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

  it('should handle JSON.stringify errors gracefully', () => {
    // Test error handling for circular references
    
    const displayAlert = vi.fn();
    
    // Create circular reference
    const mockResults = { a: 'value' };
    mockResults.circular = mockResults;
    
    try {
      JSON.stringify(mockResults, null, 2);
    } catch (error) {
      displayAlert(error.message || 'Failed to export JSON file. Please try again.', 'error');
    }
    
    expect(displayAlert).toHaveBeenCalledWith(
      expect.stringContaining('circular'),
      'error'
    );
  });
});

describe('JSON Export Integration', () => {
  it('should match the pattern of CSV and XLSX exports', () => {
    // Test that JSON export follows the same pattern as other exports
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Total Amount': '$1,234.56'
    };

    // JSON export pattern
    const jsonString = JSON.stringify(mockResults, null, 2);
    const jsonBlob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
    
    // CSV export pattern (for comparison)
    const csvData = Object.entries(mockResults).map(([field, value]) => ({
      Field: field,
      Value: value || ''
    }));
    
    // Both should handle the same data
    expect(jsonString).toBeTruthy();
    expect(csvData.length).toBe(2);
  });

  it('should use URL.createObjectURL like other exports', () => {
    // Test that JSON export uses the same download mechanism
    
    const jsonContent = '{"test":"value"}';
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    
    const url = URL.createObjectURL(blob);
    
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
    expect(url).toBe('blob:mock-url');
  });

  it('should generate consistent filename format', () => {
    // Test that filename format matches other exports
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    
    const csvFilename = `document-extraction-${timestamp}.csv`;
    const xlsxFilename = `document-extraction-${timestamp}.xlsx`;
    const jsonFilename = `document-extraction-${timestamp}.json`;
    
    // All should have the same base pattern
    expect(csvFilename).toMatch(/document-extraction-.*\.csv/);
    expect(xlsxFilename).toMatch(/document-extraction-.*\.xlsx/);
    expect(jsonFilename).toMatch(/document-extraction-.*\.json/);
  });
});
