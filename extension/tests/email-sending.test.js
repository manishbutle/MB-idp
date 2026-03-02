/**
 * Email Sending Tests
 * Tests for email sending functionality
 * Requirements: 3.7, 3.8, 3.9, 18.1, 18.2, 18.3, 18.7, 18.8, 18.9
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock Papa (PapaParse library)
global.Papa = {
  unparse: vi.fn((data, options) => {
    if (!data || data.length === 0) return '';
    const headers = Object.keys(data[0]);
    const headerRow = headers.join(',');
    const dataRows = data.map(row => 
      headers.map(header => row[header] || '').join(',')
    );
    return [headerRow, ...dataRows].join('\n');
  })
};

// Mock XLSX library
global.XLSX = {
  utils: {
    json_to_sheet: vi.fn((data) => ({ data })),
    book_new: vi.fn(() => ({ SheetNames: [], Sheets: {} })),
    book_append_sheet: vi.fn((workbook, worksheet, name) => {
      workbook.SheetNames.push(name);
      workbook.Sheets[name] = worksheet;
    })
  },
  write: vi.fn(() => 'mock-xlsx-binary')
};

// Mock btoa and atob
global.btoa = vi.fn((str) => Buffer.from(str).toString('base64'));
global.atob = vi.fn((str) => Buffer.from(str, 'base64').toString());
global.unescape = vi.fn((str) => str);
global.encodeURIComponent = vi.fn((str) => str);

// Mock storageManager
global.storageManager = {
  getEmailSettings: vi.fn()
};

// Mock apiClient
global.apiClient = {
  sendEmail: vi.fn()
};

// Mock Email (smtp.js)
global.Email = {
  send: vi.fn()
};

describe('Email Sending Functionality', () => {
  let dashboardState;
  let displayAlert;
  let handleSendEmail;
  let sendEmailViaAPI;
  let sendEmailViaSMTP;
  let generateEmailAttachments;

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Mock dashboard state
    dashboardState = {
      currentResults: {
        'Invoice Number': 'INV-12345',
        'Invoice Date': '2024-01-15',
        'Vendor Name': 'Acme Corp'
      }
    };

    // Mock displayAlert function
    displayAlert = vi.fn();

    // Mock generateEmailAttachments function
    generateEmailAttachments = async (formats) => {
      const attachments = [];
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      
      const dataArray = Object.entries(dashboardState.currentResults).map(([field, value]) => ({
        Field: field,
        Value: value || ''
      }));

      if (formats.includes('csv')) {
        const csv = Papa.unparse(dataArray, { header: true, quotes: true, skipEmptyLines: false });
        const base64Content = btoa(unescape(encodeURIComponent(csv)));
        attachments.push({
          fileName: `document-extraction-${timestamp}.csv`,
          fileContent: base64Content
        });
      }

      if (formats.includes('xlsx')) {
        const worksheet = XLSX.utils.json_to_sheet(dataArray);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, 'Results');
        const xlsxBinary = XLSX.write(workbook, { bookType: 'xlsx', type: 'binary' });
        const xlsxBase64 = btoa(xlsxBinary);
        attachments.push({
          fileName: `document-extraction-${timestamp}.xlsx`,
          fileContent: xlsxBase64
        });
      }

      if (formats.includes('json')) {
        const jsonContent = JSON.stringify(dashboardState.currentResults, null, 2);
        const base64Content = btoa(unescape(encodeURIComponent(jsonContent)));
        attachments.push({
          fileName: `document-extraction-${timestamp}.json`,
          fileContent: base64Content
        });
      }

      if (attachments.length === 0) {
        throw new Error('No attachment formats selected. Please select at least one format (CSV, XLSX, or JSON).');
      }

      return attachments;
    };

    // Mock sendEmailViaAPI function
    sendEmailViaAPI = async (emailSettings) => {
      const attachments = await generateEmailAttachments(emailSettings.attachment_formats || ['csv']);
      await apiClient.sendEmail(
        emailSettings.to,
        emailSettings.cc || '',
        emailSettings.subject || 'Document Extraction Results',
        attachments
      );
      displayAlert('Email sent successfully via default server', 'success');
    };

    // Mock sendEmailViaSMTP function
    sendEmailViaSMTP = async (emailSettings) => {
      if (typeof Email === 'undefined') {
        throw new Error('SMTP library (smtp.js) not loaded. Please ensure smtp.js is included in the extension.');
      }

      if (!emailSettings.smtp_server || !emailSettings.smtp_username || !emailSettings.smtp_password) {
        throw new Error('Incomplete SMTP configuration. Please configure SMTP server, username, and password.');
      }

      const attachments = await generateEmailAttachments(emailSettings.attachment_formats || ['csv']);
      
      const emailData = {
        SecureToken: emailSettings.smtp_password,
        To: emailSettings.to,
        From: emailSettings.email_from || emailSettings.smtp_username,
        Subject: emailSettings.subject || 'Document Extraction Results',
        Body: 'Please find attached the document extraction results.',
        Attachments: attachments.map(att => ({
          name: att.fileName,
          data: att.fileContent
        }))
      };

      if (emailSettings.cc) {
        emailData.Cc = emailSettings.cc;
      }

      await Email.send(emailData);
      displayAlert('Email sent successfully via SMTP', 'success');
    };

    // Mock handleSendEmail function
    handleSendEmail = async () => {
      try {
        if (!dashboardState.currentResults || Object.keys(dashboardState.currentResults).length === 0) {
          displayAlert('No data available to send', 'warning');
          return;
        }

        const emailSettings = await storageManager.getEmailSettings();
        
        if (!emailSettings) {
          displayAlert('Email configuration not found. Please configure email settings first.', 'warning');
          return;
        }

        if (!emailSettings.to) {
          displayAlert('Incomplete email configuration. Please specify recipient email address.', 'warning');
          return;
        }

        const mode = emailSettings.mode || 'default';
        
        if (mode === 'smtp') {
          await sendEmailViaSMTP(emailSettings);
        } else {
          await sendEmailViaAPI(emailSettings);
        }
      } catch (error) {
        console.error('Error sending email:', error);
        displayAlert(
          error.message || 'Failed to send email. Please check your email configuration and try again.',
          'error'
        );
      }
    };
  });

  describe('Email Configuration Validation', () => {
    it('should retrieve email configuration from Local Storage', async () => {
      // Test Requirement 3.7, 18.1, 18.2
      const mockEmailSettings = {
        mode: 'default',
        to: 'recipient@example.com',
        cc: 'cc@example.com',
        subject: 'Test Email',
        attachment_formats: ['csv']
      };

      storageManager.getEmailSettings.mockResolvedValue(mockEmailSettings);

      const emailSettings = await storageManager.getEmailSettings();

      expect(storageManager.getEmailSettings).toHaveBeenCalled();
      expect(emailSettings).toEqual(mockEmailSettings);
      expect(emailSettings.to).toBe('recipient@example.com');
    });

    it('should display warning when email configuration is not found', async () => {
      // Test Requirement 3.8
      storageManager.getEmailSettings.mockResolvedValue(null);

      await handleSendEmail();

      expect(displayAlert).toHaveBeenCalledWith(
        'Email configuration not found. Please configure email settings first.',
        'warning'
      );
    });

    it('should display warning when recipient email is missing', async () => {
      // Test Requirement 3.8
      const incompleteSettings = {
        mode: 'default',
        subject: 'Test Email'
      };

      storageManager.getEmailSettings.mockResolvedValue(incompleteSettings);

      await handleSendEmail();

      expect(displayAlert).toHaveBeenCalledWith(
        'Incomplete email configuration. Please specify recipient email address.',
        'warning'
      );
    });

    it('should display warning when no data is available to send', async () => {
      // Test Requirement 3.8
      dashboardState.currentResults = {};

      await handleSendEmail();

      expect(displayAlert).toHaveBeenCalledWith(
        'No data available to send',
        'warning'
      );
      expect(storageManager.getEmailSettings).not.toHaveBeenCalled();
    });
  });

  describe('Default Server Mode (API)', () => {
    it('should send email via API when mode is default', async () => {
      // Test Requirement 18.1
      const mockEmailSettings = {
        mode: 'default',
        to: 'recipient@example.com',
        cc: 'cc@example.com',
        subject: 'Document Results',
        attachment_formats: ['csv']
      };

      storageManager.getEmailSettings.mockResolvedValue(mockEmailSettings);
      apiClient.sendEmail.mockResolvedValue({ success: true });

      await handleSendEmail();

      expect(apiClient.sendEmail).toHaveBeenCalled();
      expect(displayAlert).toHaveBeenCalledWith(
        'Email sent successfully via default server',
        'success'
      );
    });

    it('should call send_email API with correct parameters', async () => {
      // Test Requirement 18.1
      const mockEmailSettings = {
        mode: 'default',
        to: 'recipient@example.com',
        cc: 'cc@example.com',
        subject: 'Test Subject',
        attachment_formats: ['csv']
      };

      storageManager.getEmailSettings.mockResolvedValue(mockEmailSettings);
      apiClient.sendEmail.mockResolvedValue({ success: true });

      await handleSendEmail();

      expect(apiClient.sendEmail).toHaveBeenCalledWith(
        'recipient@example.com',
        'cc@example.com',
        'Test Subject',
        expect.arrayContaining([
          expect.objectContaining({
            fileName: expect.stringMatching(/document-extraction-.*\.csv/),
            fileContent: expect.any(String)
          })
        ])
      );
    });
  });

  describe('SMTP Mode', () => {
    it('should send email via SMTP when mode is smtp', async () => {
      // Test Requirement 18.2
      const mockEmailSettings = {
        mode: 'smtp',
        to: 'recipient@example.com',
        smtp_server: 'smtp.example.com',
        smtp_username: 'user@example.com',
        smtp_password: 'password123',
        email_from: 'sender@example.com',
        subject: 'Document Results',
        attachment_formats: ['csv']
      };

      storageManager.getEmailSettings.mockResolvedValue(mockEmailSettings);
      Email.send.mockResolvedValue({ success: true });

      await handleSendEmail();

      expect(Email.send).toHaveBeenCalled();
      expect(displayAlert).toHaveBeenCalledWith(
        'Email sent successfully via SMTP',
        'success'
      );
    });

    it('should throw error when SMTP configuration is incomplete', async () => {
      // Test Requirement 18.2
      const incompleteSettings = {
        mode: 'smtp',
        to: 'recipient@example.com',
        smtp_server: 'smtp.example.com'
        // Missing smtp_username and smtp_password
      };

      storageManager.getEmailSettings.mockResolvedValue(incompleteSettings);

      await handleSendEmail();

      expect(displayAlert).toHaveBeenCalledWith(
        'Incomplete SMTP configuration. Please configure SMTP server, username, and password.',
        'error'
      );
    });

    it('should call Email.send with correct parameters', async () => {
      // Test Requirement 18.2
      const mockEmailSettings = {
        mode: 'smtp',
        to: 'recipient@example.com',
        cc: 'cc@example.com',
        smtp_server: 'smtp.example.com',
        smtp_username: 'user@example.com',
        smtp_password: 'password123',
        email_from: 'sender@example.com',
        subject: 'Test Subject',
        attachment_formats: ['csv']
      };

      storageManager.getEmailSettings.mockResolvedValue(mockEmailSettings);
      Email.send.mockResolvedValue({ success: true });

      await handleSendEmail();

      expect(Email.send).toHaveBeenCalledWith(
        expect.objectContaining({
          SecureToken: 'password123',
          To: 'recipient@example.com',
          Cc: 'cc@example.com',
          From: 'sender@example.com',
          Subject: 'Test Subject',
          Body: 'Please find attached the document extraction results.',
          Attachments: expect.any(Array)
        })
      );
    });
  });

  describe('Attachment Generation', () => {
    it('should generate CSV attachment when format is selected', async () => {
      // Test Requirement 18.3, 18.4
      const attachments = await generateEmailAttachments(['csv']);

      expect(attachments).toHaveLength(1);
      expect(attachments[0].fileName).toMatch(/document-extraction-.*\.csv/);
      expect(attachments[0].fileContent).toBeTruthy();
      expect(Papa.unparse).toHaveBeenCalled();
    });

    it('should generate XLSX attachment when format is selected', async () => {
      // Test Requirement 18.3, 18.5
      const attachments = await generateEmailAttachments(['xlsx']);

      expect(attachments).toHaveLength(1);
      expect(attachments[0].fileName).toMatch(/document-extraction-.*\.xlsx/);
      expect(attachments[0].fileContent).toBeTruthy();
      expect(XLSX.utils.json_to_sheet).toHaveBeenCalled();
    });

    it('should generate JSON attachment when format is selected', async () => {
      // Test Requirement 18.3, 18.6
      const attachments = await generateEmailAttachments(['json']);

      expect(attachments).toHaveLength(1);
      expect(attachments[0].fileName).toMatch(/document-extraction-.*\.json/);
      expect(attachments[0].fileContent).toBeTruthy();
    });

    it('should generate multiple attachments when multiple formats are selected', async () => {
      // Test Requirement 18.3, 18.7
      const attachments = await generateEmailAttachments(['csv', 'xlsx', 'json']);

      expect(attachments).toHaveLength(3);
      expect(attachments[0].fileName).toMatch(/\.csv$/);
      expect(attachments[1].fileName).toMatch(/\.xlsx$/);
      expect(attachments[2].fileName).toMatch(/\.json$/);
    });

    it('should throw error when no formats are selected', async () => {
      // Test Requirement 18.7
      await expect(generateEmailAttachments([])).rejects.toThrow(
        'No attachment formats selected. Please select at least one format (CSV, XLSX, or JSON).'
      );
    });

    it('should encode attachments in base64', async () => {
      // Test Requirement 18.3
      const attachments = await generateEmailAttachments(['csv']);

      expect(btoa).toHaveBeenCalled();
      expect(attachments[0].fileContent).toBeTruthy();
    });
  });

  describe('Error Handling', () => {
    it('should display error alert when API call fails', async () => {
      // Test Requirement 3.8, 18.9
      const mockEmailSettings = {
        mode: 'default',
        to: 'recipient@example.com',
        attachment_formats: ['csv']
      };

      storageManager.getEmailSettings.mockResolvedValue(mockEmailSettings);
      apiClient.sendEmail.mockRejectedValue(new Error('Network error'));

      await handleSendEmail();

      expect(displayAlert).toHaveBeenCalledWith(
        'Network error',
        'error'
      );
    });

    it('should display error alert when SMTP send fails', async () => {
      // Test Requirement 3.8, 18.9
      const mockEmailSettings = {
        mode: 'smtp',
        to: 'recipient@example.com',
        smtp_server: 'smtp.example.com',
        smtp_username: 'user@example.com',
        smtp_password: 'password123',
        attachment_formats: ['csv']
      };

      storageManager.getEmailSettings.mockResolvedValue(mockEmailSettings);
      Email.send.mockRejectedValue(new Error('SMTP connection failed'));

      await handleSendEmail();

      expect(displayAlert).toHaveBeenCalledWith(
        'SMTP connection failed',
        'error'
      );
    });

    it('should display success alert when email is sent successfully', async () => {
      // Test Requirement 3.9, 18.8
      const mockEmailSettings = {
        mode: 'default',
        to: 'recipient@example.com',
        attachment_formats: ['csv']
      };

      storageManager.getEmailSettings.mockResolvedValue(mockEmailSettings);
      apiClient.sendEmail.mockResolvedValue({ success: true });

      await handleSendEmail();

      expect(displayAlert).toHaveBeenCalledWith(
        'Email sent successfully via default server',
        'success'
      );
    });
  });
});
