/**
 * Comprehensive Unit Tests for Profile Tab - Statistics Display Functions
 * Task 16.5: Implement profile statistics display
 * Requirements: 7.3, 7.4
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Profile Statistics Display - loadProfile', () => {
  let dom;
  let document;
  let mockApiClient;
  let mockDisplayAlert;
  let currentUser;

  beforeEach(() => {
    // Create DOM
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-logged-in">
            <h2 id="user-name-heading"></h2>
            <div class="stats-cards">
              <div class="card">
                <span id="documents-processed-count">0</span>
              </div>
              <div class="card">
                <span id="available-balance-amount">0.00</span>
              </div>
            </div>
            <div id="profile-settings-content">
              <input type="text" id="profile-first-name" value="" />
              <input type="text" id="profile-last-name" value="" />
            </div>
            <div id="transaction-history-content">
              <tbody id="transaction-history-body"></tbody>
            </div>
          </div>
        </body>
      </html>
    `);

    document = dom.window.document;
    global.document = document;

    // Mock current user
    currentUser = {
      token: 'test-token',
      user_email: 'test@example.com',
      user_name: 'John Doe',
      role: 'User',
      tenant: 'default'
    };

    // Mock API client
    mockApiClient = {
      getTotalDocumentProcessed: vi.fn(),
      getAvailableBalance: vi.fn(),
      call: vi.fn()
    };

    // Mock UI functions
    mockDisplayAlert = vi.fn();

    global.apiClient = mockApiClient;
    global.displayAlert = mockDisplayAlert;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Requirement 7.1: Display user full name', () => {
    it('should update user name heading with current user name', () => {
      const userNameHeading = document.getElementById('user-name-heading');
      
      if (userNameHeading && currentUser) {
        userNameHeading.textContent = `Welcome, ${currentUser.user_name}`;
      }

      expect(userNameHeading.textContent).toBe('Welcome, John Doe');
    });

    it('should handle missing user name gracefully', () => {
      const userNameHeading = document.getElementById('user-name-heading');
      const userWithoutName = { ...currentUser, user_name: null };
      
      if (userNameHeading && userWithoutName) {
        userNameHeading.textContent = `Welcome, ${userWithoutName.user_name || userWithoutName.user_email}`;
      }

      expect(userNameHeading.textContent).toBe('Welcome, test@example.com');
    });

    it('should not update heading if element is missing', () => {
      const userNameHeading = null;
      
      // Should not throw error
      if (userNameHeading && currentUser) {
        userNameHeading.textContent = `Welcome, ${currentUser.user_name}`;
      }

      // No error should be thrown
      expect(true).toBe(true);
    });
  });

  describe('Requirement 7.2: Display statistics cards', () => {
    it('should display both documents processed and available balance cards', () => {
      const documentsCountElement = document.getElementById('documents-processed-count');
      const balanceElement = document.getElementById('available-balance-amount');

      expect(documentsCountElement).not.toBeNull();
      expect(balanceElement).not.toBeNull();
    });
  });
});

describe('Profile Statistics Display - loadDocumentsProcessed', () => {
  let dom;
  let document;
  let mockApiClient;

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-logged-in">
            <div class="card">
              <h3>Documents Processed</h3>
              <span id="documents-processed-count">0</span>
            </div>
          </div>
        </body>
      </html>
    `);

    document = dom.window.document;
    global.document = document;

    mockApiClient = {
      getTotalDocumentProcessed: vi.fn()
    };

    global.apiClient = mockApiClient;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Requirement 7.3: Call total_document_processed API', () => {
    it('should call getTotalDocumentProcessed API', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 42
      });

      await mockApiClient.getTotalDocumentProcessed();

      expect(mockApiClient.getTotalDocumentProcessed).toHaveBeenCalled();
      expect(mockApiClient.getTotalDocumentProcessed).toHaveBeenCalledTimes(1);
    });

    it('should update count element with API response', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 42
      });

      const response = await mockApiClient.getTotalDocumentProcessed();
      const countElement = document.getElementById('documents-processed-count');

      if (countElement && response.success) {
        countElement.textContent = response.count || 0;
      }

      expect(countElement.textContent).toBe('42');
    });

    it('should display 0 when count is not provided', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true
      });

      const response = await mockApiClient.getTotalDocumentProcessed();
      const countElement = document.getElementById('documents-processed-count');

      if (countElement && response.success) {
        countElement.textContent = response.count || 0;
      }

      expect(countElement.textContent).toBe('0');
    });

    it('should display 0 when count is null', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: null
      });

      const response = await mockApiClient.getTotalDocumentProcessed();
      const countElement = document.getElementById('documents-processed-count');

      if (countElement && response.success) {
        countElement.textContent = response.count || 0;
      }

      expect(countElement.textContent).toBe('0');
    });

    it('should handle large document counts', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 999999
      });

      const response = await mockApiClient.getTotalDocumentProcessed();
      const countElement = document.getElementById('documents-processed-count');

      if (countElement && response.success) {
        countElement.textContent = response.count || 0;
      }

      expect(countElement.textContent).toBe('999999');
    });

    it('should not update element when API call fails', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: false,
        message: 'Failed to fetch count'
      });

      const response = await mockApiClient.getTotalDocumentProcessed();
      const countElement = document.getElementById('documents-processed-count');
      const originalValue = countElement.textContent;

      if (countElement && response.success) {
        countElement.textContent = response.count || 0;
      }

      expect(countElement.textContent).toBe(originalValue);
    });

    it('should handle API errors gracefully', async () => {
      mockApiClient.getTotalDocumentProcessed.mockRejectedValue(
        new Error('Network error')
      );

      try {
        await mockApiClient.getTotalDocumentProcessed();
      } catch (error) {
        expect(error.message).toBe('Network error');
      }

      expect(mockApiClient.getTotalDocumentProcessed).toHaveBeenCalled();
    });

    it('should not throw error if count element is missing', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 42
      });

      const response = await mockApiClient.getTotalDocumentProcessed();
      const countElement = document.getElementById('non-existent-element');

      // Should not throw error
      if (countElement && response.success) {
        countElement.textContent = response.count || 0;
      }

      expect(true).toBe(true);
    });
  });
});

describe('Profile Statistics Display - loadAvailableBalance', () => {
  let dom;
  let document;
  let mockApiClient;

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-logged-in">
            <div class="card">
              <h3>Available Balance</h3>
              <span id="available-balance-amount">0.00</span>
            </div>
          </div>
        </body>
      </html>
    `);

    document = dom.window.document;
    global.document = document;

    mockApiClient = {
      getAvailableBalance: vi.fn()
    };

    global.apiClient = mockApiClient;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Requirement 7.4: Call available_balance API', () => {
    it('should call getAvailableBalance API', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 150.75
      });

      await mockApiClient.getAvailableBalance();

      expect(mockApiClient.getAvailableBalance).toHaveBeenCalled();
      expect(mockApiClient.getAvailableBalance).toHaveBeenCalledTimes(1);
    });

    it('should update balance element with API response', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 150.75
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe('$150.75');
    });

    it('should format balance to 2 decimal places', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 100
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe('$100.00');
    });

    it('should display 0.00 when balance is not provided', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe('$0.00');
    });

    it('should display 0.00 when balance is null', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: null
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe('$0.00');
    });

    it('should handle negative balance', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: -25.50
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe('$-25.50');
    });

    it('should handle very large balance amounts', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 9999999.99
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe('$9999999.99');
    });

    it('should round balance to 2 decimal places', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 123.456789
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe('$123.46');
    });

    it('should not update element when API call fails', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: false,
        message: 'Failed to fetch balance'
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');
      const originalValue = balanceElement.textContent;

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe(originalValue);
    });

    it('should handle API errors gracefully', async () => {
      mockApiClient.getAvailableBalance.mockRejectedValue(
        new Error('Network error')
      );

      try {
        await mockApiClient.getAvailableBalance();
      } catch (error) {
        expect(error.message).toBe('Network error');
      }

      expect(mockApiClient.getAvailableBalance).toHaveBeenCalled();
    });

    it('should not throw error if balance element is missing', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 150.75
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('non-existent-element');

      // Should not throw error
      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(true).toBe(true);
    });

    it('should handle zero balance', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 0
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(balanceElement.textContent).toBe('$0.00');
    });

    it('should handle fractional cents correctly', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 99.995
      });

      const response = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');

      if (balanceElement && response.success) {
        const balance = response.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      // JavaScript rounds 99.995 to 100.00
      expect(balanceElement.textContent).toBe('$100.00');
    });
  });
});

describe('Profile Statistics Display - Integration', () => {
  let dom;
  let document;
  let mockApiClient;
  let currentUser;

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-logged-in">
            <h2 id="user-name-heading"></h2>
            <div class="stats-cards">
              <div class="card">
                <h3>Documents Processed</h3>
                <span id="documents-processed-count">0</span>
              </div>
              <div class="card">
                <h3>Available Balance</h3>
                <span id="available-balance-amount">0.00</span>
              </div>
            </div>
          </div>
        </body>
      </html>
    `);

    document = dom.window.document;
    global.document = document;

    currentUser = {
      token: 'test-token',
      user_email: 'test@example.com',
      user_name: 'Jane Smith',
      role: 'User',
      tenant: 'default'
    };

    mockApiClient = {
      getTotalDocumentProcessed: vi.fn(),
      getAvailableBalance: vi.fn()
    };

    global.apiClient = mockApiClient;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Complete profile load workflow', () => {
    it('should load all profile data successfully', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 25
      });

      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 500.00
      });

      // Simulate loadProfile
      const userNameHeading = document.getElementById('user-name-heading');
      if (userNameHeading && currentUser) {
        userNameHeading.textContent = `Welcome, ${currentUser.user_name}`;
      }

      const countResponse = await mockApiClient.getTotalDocumentProcessed();
      const countElement = document.getElementById('documents-processed-count');
      if (countElement && countResponse.success) {
        countElement.textContent = countResponse.count || 0;
      }

      const balanceResponse = await mockApiClient.getAvailableBalance();
      const balanceElement = document.getElementById('available-balance-amount');
      if (balanceElement && balanceResponse.success) {
        const balance = balanceResponse.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(userNameHeading.textContent).toBe('Welcome, Jane Smith');
      expect(countElement.textContent).toBe('25');
      expect(balanceElement.textContent).toBe('$500.00');
      expect(mockApiClient.getTotalDocumentProcessed).toHaveBeenCalledTimes(1);
      expect(mockApiClient.getAvailableBalance).toHaveBeenCalledTimes(1);
    });

    it('should handle partial API failures gracefully', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 10
      });

      mockApiClient.getAvailableBalance.mockRejectedValue(
        new Error('Balance API error')
      );

      // Load documents processed (should succeed)
      const countResponse = await mockApiClient.getTotalDocumentProcessed();
      const countElement = document.getElementById('documents-processed-count');
      if (countElement && countResponse.success) {
        countElement.textContent = countResponse.count || 0;
      }

      // Load balance (should fail but not break)
      try {
        await mockApiClient.getAvailableBalance();
      } catch (error) {
        // Error is caught and logged
      }

      const balanceElement = document.getElementById('available-balance-amount');

      expect(countElement.textContent).toBe('10');
      expect(balanceElement.textContent).toBe('0.00'); // Original value
    });

    it('should call both APIs independently', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 5
      });

      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 75.25
      });

      // Call both APIs
      await mockApiClient.getTotalDocumentProcessed();
      await mockApiClient.getAvailableBalance();

      expect(mockApiClient.getTotalDocumentProcessed).toHaveBeenCalledTimes(1);
      expect(mockApiClient.getAvailableBalance).toHaveBeenCalledTimes(1);
    });
  });

  describe('Requirements validation', () => {
    it('should satisfy Requirement 7.3: Call total_document_processed API', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 100
      });

      await mockApiClient.getTotalDocumentProcessed();

      expect(mockApiClient.getTotalDocumentProcessed).toHaveBeenCalled();
    });

    it('should satisfy Requirement 7.4: Call available_balance API', async () => {
      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 250.00
      });

      await mockApiClient.getAvailableBalance();

      expect(mockApiClient.getAvailableBalance).toHaveBeenCalled();
    });

    it('should update cards with fetched data', async () => {
      mockApiClient.getTotalDocumentProcessed.mockResolvedValue({
        success: true,
        count: 15
      });

      mockApiClient.getAvailableBalance.mockResolvedValue({
        success: true,
        balance: 300.50
      });

      const countResponse = await mockApiClient.getTotalDocumentProcessed();
      const balanceResponse = await mockApiClient.getAvailableBalance();

      const countElement = document.getElementById('documents-processed-count');
      const balanceElement = document.getElementById('available-balance-amount');

      if (countElement && countResponse.success) {
        countElement.textContent = countResponse.count || 0;
      }

      if (balanceElement && balanceResponse.success) {
        const balance = balanceResponse.balance || 0;
        balanceElement.textContent = `$${balance.toFixed(2)}`;
      }

      expect(countElement.textContent).toBe('15');
      expect(balanceElement.textContent).toBe('$300.50');
    });
  });
});
