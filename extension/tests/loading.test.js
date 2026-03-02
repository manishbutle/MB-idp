/**
 * Unit Tests for Loading Indicator Component
 * Tests loading indicator functionality and UI responsiveness
 * Requirements: 15.2, 15.3, 15.4
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Loading Indicator Component', () => {
  let dom;
  let document;
  let window;

  beforeEach(() => {
    // Create a fresh DOM for each test
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="loading-overlay" class="hidden">
            <div>
              <div class="spinner"></div>
              <p>Processing...</p>
            </div>
          </div>
        </body>
      </html>
    `);
    
    document = dom.window.document;
    window = dom.window;
    global.document = document;
    global.window = window;

    // Load the loading.js module
    const loadingScript = require('fs').readFileSync('./scripts/loading.js', 'utf8');
    eval(loadingScript);
  });

  afterEach(() => {
    // Clean up
    delete global.document;
    delete global.window;
  });

  describe('showLoading', () => {
    it('should show loading overlay when called', () => {
      // Requirement 15.2: Display loading indicator
      const overlay = document.getElementById('loading-overlay');
      expect(overlay.classList.contains('hidden')).toBe(true);

      window.showLoading();

      expect(overlay.classList.contains('hidden')).toBe(false);
    });

    it('should display default message when no message provided', () => {
      window.showLoading();

      const messageElement = document.querySelector('#loading-overlay p');
      expect(messageElement.textContent).toBe('Processing...');
    });

    it('should display custom message when provided', () => {
      const customMessage = 'Loading data...';
      window.showLoading(customMessage);

      const messageElement = document.querySelector('#loading-overlay p');
      expect(messageElement.textContent).toBe(customMessage);
    });

    it('should handle missing overlay element gracefully', () => {
      // Remove the overlay element
      const overlay = document.getElementById('loading-overlay');
      overlay.remove();

      // Should not throw error
      expect(() => window.showLoading()).not.toThrow();
    });

    it('should log error when overlay element not found', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      // Remove the overlay element
      const overlay = document.getElementById('loading-overlay');
      overlay.remove();

      window.showLoading();

      expect(consoleErrorSpy).toHaveBeenCalledWith('Loading overlay element not found');
      consoleErrorSpy.mockRestore();
    });
  });

  describe('hideLoading', () => {
    it('should hide loading overlay when called', () => {
      // Requirement 15.3: Hide loading indicator when processing completes
      const overlay = document.getElementById('loading-overlay');
      
      // First show the loading
      window.showLoading();
      expect(overlay.classList.contains('hidden')).toBe(false);

      // Then hide it
      window.hideLoading();
      expect(overlay.classList.contains('hidden')).toBe(true);
    });

    it('should reset message to default when hiding', () => {
      // Show with custom message
      window.showLoading('Custom message');
      
      const messageElement = document.querySelector('#loading-overlay p');
      expect(messageElement.textContent).toBe('Custom message');

      // Hide loading
      window.hideLoading();

      // Message should be reset to default
      expect(messageElement.textContent).toBe('Processing...');
    });

    it('should handle missing overlay element gracefully', () => {
      // Remove the overlay element
      const overlay = document.getElementById('loading-overlay');
      overlay.remove();

      // Should not throw error
      expect(() => window.hideLoading()).not.toThrow();
    });

    it('should log error when overlay element not found', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      // Remove the overlay element
      const overlay = document.getElementById('loading-overlay');
      overlay.remove();

      window.hideLoading();

      expect(consoleErrorSpy).toHaveBeenCalledWith('Loading overlay element not found');
      consoleErrorSpy.mockRestore();
    });
  });

  describe('isLoading', () => {
    it('should return false when loading is not visible', () => {
      expect(window.isLoading()).toBe(false);
    });

    it('should return true when loading is visible', () => {
      window.showLoading();
      expect(window.isLoading()).toBe(true);
    });

    it('should return false after hiding loading', () => {
      window.showLoading();
      expect(window.isLoading()).toBe(true);
      
      window.hideLoading();
      expect(window.isLoading()).toBe(false);
    });

    it('should return false when overlay element not found', () => {
      // Remove the overlay element
      const overlay = document.getElementById('loading-overlay');
      overlay.remove();

      expect(window.isLoading()).toBe(false);
    });
  });

  describe('withLoading', () => {
    it('should show loading before async operation and hide after completion', async () => {
      // Requirement 15.2, 15.3: Show loading during operation, hide after completion
      const asyncOperation = vi.fn(async () => {
        // Simulate async work
        await new Promise(resolve => setTimeout(resolve, 10));
        return 'result';
      });

      const overlay = document.getElementById('loading-overlay');
      expect(overlay.classList.contains('hidden')).toBe(true);

      const resultPromise = window.withLoading(asyncOperation);
      
      // Loading should be visible during operation
      expect(overlay.classList.contains('hidden')).toBe(false);

      const result = await resultPromise;

      // Loading should be hidden after completion
      expect(overlay.classList.contains('hidden')).toBe(true);
      expect(result).toBe('result');
      expect(asyncOperation).toHaveBeenCalledTimes(1);
    });

    it('should use custom message when provided', async () => {
      const customMessage = 'Loading data...';
      const asyncOperation = async () => 'result';

      window.withLoading(asyncOperation, customMessage);

      const messageElement = document.querySelector('#loading-overlay p');
      expect(messageElement.textContent).toBe(customMessage);
    });

    it('should hide loading even if async operation throws error', async () => {
      // Requirement 15.3: Hide loading indicator even on error
      const error = new Error('Operation failed');
      const asyncOperation = vi.fn(async () => {
        throw error;
      });

      const overlay = document.getElementById('loading-overlay');

      try {
        await window.withLoading(asyncOperation);
        // Should not reach here
        expect(true).toBe(false);
      } catch (err) {
        expect(err).toBe(error);
        // Loading should be hidden even after error
        expect(overlay.classList.contains('hidden')).toBe(true);
      }
    });

    it('should propagate the error from async operation', async () => {
      const error = new Error('Test error');
      const asyncOperation = async () => {
        throw error;
      };

      await expect(window.withLoading(asyncOperation)).rejects.toThrow('Test error');
    });

    it('should return the result from async operation', async () => {
      const expectedResult = { data: 'test', count: 42 };
      const asyncOperation = async () => expectedResult;

      const result = await window.withLoading(asyncOperation);

      expect(result).toEqual(expectedResult);
    });
  });

  describe('UI Responsiveness', () => {
    it('should not block other UI elements when loading is shown', () => {
      // Requirement 15.4: Ensure UI remains responsive during loading
      const overlay = document.getElementById('loading-overlay');
      
      // Add a button outside the overlay
      const button = document.createElement('button');
      button.id = 'test-button';
      button.textContent = 'Click me';
      document.body.appendChild(button);

      // Show loading
      window.showLoading();

      // The overlay should be visible
      expect(overlay.classList.contains('hidden')).toBe(false);

      // The button should still be accessible in the DOM
      const foundButton = document.getElementById('test-button');
      expect(foundButton).not.toBeNull();
      expect(foundButton.textContent).toBe('Click me');

      // Clean up
      button.remove();
    });

    it('should allow multiple show/hide cycles without issues', () => {
      // Test that the loading indicator can be shown and hidden multiple times
      const overlay = document.getElementById('loading-overlay');

      for (let i = 0; i < 5; i++) {
        window.showLoading(`Loading ${i}...`);
        expect(overlay.classList.contains('hidden')).toBe(false);
        
        window.hideLoading();
        expect(overlay.classList.contains('hidden')).toBe(true);
      }
    });

    it('should handle rapid show/hide calls gracefully', () => {
      // Simulate rapid calls that might happen in real usage
      window.showLoading();
      window.showLoading();
      window.hideLoading();
      window.hideLoading();
      window.showLoading();
      window.hideLoading();

      const overlay = document.getElementById('loading-overlay');
      expect(overlay.classList.contains('hidden')).toBe(true);
    });
  });

  describe('Integration with async operations', () => {
    it('should work correctly with Promise-based operations', async () => {
      const asyncOp = () => Promise.resolve('success');
      
      const result = await window.withLoading(asyncOp);
      
      expect(result).toBe('success');
      expect(window.isLoading()).toBe(false);
    });

    it('should work correctly with async/await operations', async () => {
      const asyncOp = async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
        return 'completed';
      };
      
      const result = await window.withLoading(asyncOp);
      
      expect(result).toBe('completed');
      expect(window.isLoading()).toBe(false);
    });

    it('should handle nested async operations', async () => {
      const innerOp = async () => {
        await new Promise(resolve => setTimeout(resolve, 5));
        return 'inner';
      };

      const outerOp = async () => {
        const innerResult = await innerOp();
        return `outer-${innerResult}`;
      };

      const result = await window.withLoading(outerOp);

      expect(result).toBe('outer-inner');
      expect(window.isLoading()).toBe(false);
    });
  });

  describe('Edge cases', () => {
    it('should handle empty message string', () => {
      window.showLoading('');

      const messageElement = document.querySelector('#loading-overlay p');
      // Empty string should use default message (more sensible behavior)
      expect(messageElement.textContent).toBe('Processing...');
    });

    it('should handle very long message strings', () => {
      const longMessage = 'A'.repeat(1000);
      window.showLoading(longMessage);

      const messageElement = document.querySelector('#loading-overlay p');
      expect(messageElement.textContent).toBe(longMessage);
    });

    it('should handle special characters in message', () => {
      const specialMessage = '<script>alert("xss")</script>';
      window.showLoading(specialMessage);

      const messageElement = document.querySelector('#loading-overlay p');
      // textContent should safely handle special characters
      expect(messageElement.textContent).toBe(specialMessage);
    });

    it('should handle null message parameter', () => {
      window.showLoading(null);

      const messageElement = document.querySelector('#loading-overlay p');
      // Should use default message when null is passed
      expect(messageElement.textContent).toBe('Processing...');
    });

    it('should handle undefined message parameter', () => {
      window.showLoading(undefined);

      const messageElement = document.querySelector('#loading-overlay p');
      // Should use default message when undefined is passed
      expect(messageElement.textContent).toBe('Processing...');
    });
  });
});
