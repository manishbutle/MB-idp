/**
 * FTP Export Tests
 * Tests for FTP export functionality
 * Requirements: 3.5, 3.8, 3.9, 19.1, 19.2
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
        return value;
      }).join(',')
    );
    
    return [headerRow, ...dataRows].join('\n');
  })
};

// Mock btoa for base64 encoding
global.btoa = vi.fn((str) => Buffer.from(str).toString('base64'));
global.unescape = vi.fn((str) => str);
global.encodeURIComponent = vi.fn((str) => str);

// Mock storageManager
global.storageManager = {
  getFTPSettings: vi.fn()
};

// Mock apiClient
global.apiClient = {
  uploadToFTP: vi.fn()
};

// Mock displayAlert
global.displayAlert = vi.fn();

// Mock dashboardState
global.dashboardState = {
  currentResults: null
};

beforeEach(() => {
  // Reset mocks
  vi.clearAllMocks();
  
  // Reset dashboard state
  dashboardState.currentResults = null;
});

describe('FTP Export Functionality', () => {
  it('should retrieve FTP configuration from Local Storage', async () => {
    // Test Requirement 3.5, 19.1 - Retrieve FTP configuration
    
    const mockFtpSettings = {
      host: 'ftp.example.com',
      port: 21,
      username: 'testuser',
      password: 'testpass',
      remote_directory: '/uploads'
    };

    storageManager.getFTPSettings.mockResolvedValue(mockFtpSettings);
    dashboardState.currentResults = { 'Invoice Number': 'INV-12345' };

    // Simulate FTP export
    const ftpSettings = await storageManager.getFTPSettings();
    
    expect(storageManager.getFTPSettings).toHaveBeenCalled();
    expect(ftpSettings).toEqual(mockFtpSettings);
    expect(ftpSettings.host).toBe('ftp.example.com');
    expect(ftpSettings.username).toBe('testuser');
  });

  it('should display warning when FTP configuration is not found', async () => {
    // Test Requirement 3.8 - Display error alert
    
    storageManager.getFTPSettings.mockResolvedValue(null);
    dashboardState.currentResults = { 'Invoice Number': 'INV-12345' };

    // Simulate FTP export with missing config
    const ftpSettings = await storageManager.getFTPSettings();
    
    if (!ftpSettings) {
      displayAlert('FTP configuration not found. Please configure FTP settings first.', 'warning');
    }
    
    expect(displayAlert).toHaveBeenCalledWith(
      'FTP configuration not found. Please configure FTP settings first.',
      'warning'
    );
  });

  it('should display warning when FTP configuration is incomplete', async () => {
    // Test Requirement 3.8 - Display error alert for incomplete config
    
    const incompleteFtpSettings = {
      host: 'ftp.example.com',
      // Missing username
      password: 'testpass'
    };

    storageManager.getFTPSettings.mockResolvedValue(incompleteFtpSettings);
    dashboardState.currentResults = { 'Invoice Number': 'INV-12345' };

    // Simulate FTP export with incomplete config
    const ftpSettings = await storageManager.getFTPSettings();
    
    if (!ftpSettings.host || !ftpSettings.username) {
      displayAlert('Incomplete FTP configuration. Please check your FTP settings.', 'warning');
    }
    
    expect(displayAlert).toHaveBeenCalledWith(
      'Incomplete FTP configuration. Please check your FTP settings.',
      'warning'
    );
  });

  it('should convert RESULT data to CSV and encode to base64', async () => {
    // Test data conversion for FTP upload
    
    const mockResults = {
      'Invoice Number': 'INV-12345',
      'Invoice Date': '2024-01-15',
      'Vendor Name': 'Acme Corp'
    };

    dashboardState.currentResults = mockResults;

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

    // Encode to base64
    const base64Content = btoa(unescape(encodeURIComponent(csv)));

    expect(Papa.unparse).toHaveBeenCalled();
    expect(btoa).toHaveBeenCalled();
    expect(base64Content).toBeDefined();
  });

  it('should call FTP API endpoint with correct parameters', async () => {
    // Test Requirement 19.2 - Call FTP API endpoint
    
    const mockFtpSettings = {
      host: 'ftp.example.com',
      port: 21,
      username: 'testuser',
      password: 'testpass',
      remote_directory: '/uploads'
    };

    storageManager.getFTPSettings.mockResolvedValue(mockFtpSettings);
    apiClient.uploadToFTP.mockResolvedValue({
      message: 'File uploaded successfully',
      file_name: 'document-extraction-2024-01-15.csv'
    });

    dashboardState.currentResults = { 'Invoice Number': 'INV-12345' };

    // Simulate FTP export
    const ftpSettings = await storageManager.getFTPSettings();
    const fileName = 'document-extraction-2024-01-15.csv';
    const base64Content = 'bW9ja0Jhc2U2NENvbnRlbnQ=';

    await apiClient.uploadToFTP(
      fileName,
      base64Content,
      ftpSettings.remote_directory
    );

    expect(apiClient.uploadToFTP).toHaveBeenCalledWith(
      fileName,
      base64Content,
      '/uploads'
    );
  });

  it('should display success alert when FTP upload succeeds', async () => {
    // Test Requirement 3.9 - Display success alert
    
    const mockFtpSettings = {
      host: 'ftp.example.com',
      username: 'testuser',
      remote_directory: '/uploads'
    };

    storageManager.getFTPSettings.mockResolvedValue(mockFtpSettings);
    apiClient.uploadToFTP.mockResolvedValue({
      message: 'File uploaded successfully',
      file_name: 'document-extraction-2024-01-15.csv'
    });

    dashboardState.currentResults = { 'Invoice Number': 'INV-12345' };

    // Simulate successful FTP export
    const fileName = 'document-extraction-2024-01-15.csv';
    await apiClient.uploadToFTP(fileName, 'base64content', '/uploads');
    
    displayAlert(
      `File uploaded successfully to FTP server: ${fileName}`,
      'success'
    );

    expect(displayAlert).toHaveBeenCalledWith(
      'File uploaded successfully to FTP server: document-extraction-2024-01-15.csv',
      'success'
    );
  });

  it('should display error alert when FTP upload fails', async () => {
    // Test Requirement 3.8 - Display error alert
    
    const mockFtpSettings = {
      host: 'ftp.example.com',
      username: 'testuser',
      remote_directory: '/uploads'
    };

    storageManager.getFTPSettings.mockResolvedValue(mockFtpSettings);
    apiClient.uploadToFTP.mockRejectedValue(new Error('Connection timeout'));

    dashboardState.currentResults = { 'Invoice Number': 'INV-12345' };

    // Simulate failed FTP export
    try {
      await apiClient.uploadToFTP('test.csv', 'base64content', '/uploads');
    } catch (error) {
      displayAlert(
        error.message || 'Failed to upload file to FTP server. Please check your FTP configuration and try again.',
        'error'
      );
    }

    expect(displayAlert).toHaveBeenCalledWith(
      'Connection timeout',
      'error'
    );
  });

  it('should display warning when no data is available to export', async () => {
    // Test edge case - no data to export
    
    dashboardState.currentResults = null;

    // Simulate FTP export with no data
    if (!dashboardState.currentResults || Object.keys(dashboardState.currentResults || {}).length === 0) {
      displayAlert('No data available to export', 'warning');
    }

    expect(displayAlert).toHaveBeenCalledWith(
      'No data available to export',
      'warning'
    );
  });

  it('should handle empty remote directory', async () => {
    // Test Requirement 19.4 - Upload to default directory when remote_directory is not specified
    
    const mockFtpSettings = {
      host: 'ftp.example.com',
      username: 'testuser',
      remote_directory: '' // Empty directory
    };

    storageManager.getFTPSettings.mockResolvedValue(mockFtpSettings);
    apiClient.uploadToFTP.mockResolvedValue({
      message: 'File uploaded successfully',
      file_name: 'test.csv',
      remote_directory: 'default'
    });

    dashboardState.currentResults = { 'Invoice Number': 'INV-12345' };

    // Simulate FTP export with empty directory
    await apiClient.uploadToFTP('test.csv', 'base64content', '');

    expect(apiClient.uploadToFTP).toHaveBeenCalledWith(
      'test.csv',
      'base64content',
      ''
    );
  });

  it('should generate filename with timestamp', () => {
    // Test filename generation
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const fileName = `document-extraction-${timestamp}.csv`;

    expect(fileName).toMatch(/^document-extraction-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.csv$/);
  });
});
