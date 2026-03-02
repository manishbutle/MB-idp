/**
 * Unit Tests for Alert/Notification System
 * Tests Requirements: 14.1, 14.2, 14.3, 14.8
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Alert System', () => {
  let dom;
  let document;
  let window;

  beforeEach(() => {
    // Create a fresh DOM for each test
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="alert-container"></div>
        </body>
      </html>
    `, { runScripts: 'dangerously' });

    document = dom.window.document;
    window = dom.window;

    // Load the alerts.js script
    const alertsScript = require('fs').readFileSync('./scripts/alerts.js', 'utf8');
    const scriptEl = document.createElement('script');
    scriptEl.textContent = alertsScript;
    document.body.appendChild(scriptEl);

    // Mock timers
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('displayAlert function', () => {
    it('should display a success alert message', () => {
      // Requirement 14.2 - Display success alert
      window.displayAlert('Operation successful', 'success');

      const container = document.getElementById('alert-container');
      const alerts = container.querySelectorAll('.alert');

      expect(alerts.length).toBe(1);
      expect(alerts[0].textContent).toContain('Operation successful');
      expect(alerts[0].className).toContain('alert-success');
      expect(alerts[0].className).toContain('bg-green-100');
    });

    it('should display an error alert message', () => {
      // Requirement 14.1 - Display error alert
      window.displayAlert('Operation failed', 'error');

      const container = document.getElementById('alert-container');
      const alerts = container.querySelectorAll('.alert');

      expect(alerts.length).toBe(1);
      expect(alerts[0].textContent).toContain('Operation failed');
      expect(alerts[0].className).toContain('alert-error');
      expect(alerts[0].className).toContain('bg-red-100');
    });

    it('should display a warning alert message', () => {
      // Requirement 14.3 - Display warning alert
      window.displayAlert('Warning: Check your input', 'warning');

      const container = document.getElementById('alert-container');
      const alerts = container.querySelectorAll('.alert');

      expect(alerts.length).toBe(1);
      expect(alerts[0].textContent).toContain('Warning: Check your input');
      expect(alerts[0].className).toContain('alert-warning');
      expect(alerts[0].className).toContain('bg-yellow-100');
    });

    it('should display an info alert when type is not specified', () => {
      window.displayAlert('Information message');

      const container = document.getElementById('alert-container');
      const alerts = container.querySelectorAll('.alert');

      expect(alerts.length).toBe(1);
      expect(alerts[0].textContent).toContain('Information message');
      expect(alerts[0].className).toContain('alert-info');
      expect(alerts[0].className).toContain('bg-blue-100');
    });

    it('should include appropriate icon for each alert type', () => {
      window.displayAlert('Success', 'success');
      window.displayAlert('Error', 'error');
      window.displayAlert('Warning', 'warning');

      const container = document.getElementById('alert-container');
      const alerts = container.querySelectorAll('.alert');

      expect(alerts.length).toBe(3);
      expect(alerts[0].textContent).toContain('✓'); // Success icon
      expect(alerts[1].textContent).toContain('✕'); // Error icon
      expect(alerts[2].textContent).toContain('⚠'); // Warning icon
    });

    it('should include a close button', () => {
      window.displayAlert('Test message', 'info');

      const container = document.getElementById('alert-container');
      const closeBtn = container.querySelector('.alert-close');

      expect(closeBtn).toBeTruthy();
      expect(closeBtn.getAttribute('aria-label')).toBe('Close');
    });

    it('should apply consistent styling to all alerts', () => {
      // Requirement 14.8 - Consistent styling
      window.displayAlert('Message 1', 'success');
      window.displayAlert('Message 2', 'error');
      window.displayAlert('Message 3', 'warning');

      const container = document.getElementById('alert-container');
      const alerts = container.querySelectorAll('.alert');

      alerts.forEach(alert => {
        expect(alert.className).toContain('flex');
        expect(alert.className).toContain('items-center');
        expect(alert.className).toContain('justify-between');
        expect(alert.className).toContain('p-4');
        expect(alert.className).toContain('rounded-lg');
        expect(alert.className).toContain('shadow-lg');
        expect(alert.className).toContain('animate-slide-in');
      });
    });

    it('should escape HTML in messages to prevent XSS', () => {
      const maliciousMessage = '<script>alert("XSS")</script>';
      window.displayAlert(maliciousMessage, 'error');

      const container = document.getElementById('alert-container');
      const alert = container.querySelector('.alert');

      // The script tag should be escaped and not executed
      expect(alert.innerHTML).toContain('&lt;script&gt;');
      expect(alert.innerHTML).not.toContain('<script>');
    });

    it('should handle missing alert container gracefully', () => {
      // Remove the container
      const container = document.getElementById('alert-container');
      container.remove();

      // Mock console.error
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Should not throw error
      expect(() => {
        window.displayAlert('Test', 'info');
      }).not.toThrow();

      expect(consoleErrorSpy).toHaveBeenCalledWith('Alert container not found');
    });
  });

  describe('Auto-dismiss functionality', () => {
    it('should auto-dismiss success alerts after 3 seconds', () => {
      // Requirement 14.2 - Auto-dismiss success alerts after 3 seconds
      window.displayAlert('Success message', 'success');

      const container = document.getElementById('alert-container');
      let alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(1);

      // Fast-forward time by 3 seconds
      vi.advanceTimersByTime(3000);

      // Wait for animation to complete
      vi.advanceTimersByTime(300);

      alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(0);
    });

    it('should auto-dismiss error alerts after 5 seconds', () => {
      window.displayAlert('Error message', 'error');

      const container = document.getElementById('alert-container');
      let alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(1);

      // Fast-forward time by 5 seconds
      vi.advanceTimersByTime(5000);

      // Wait for animation to complete
      vi.advanceTimersByTime(300);

      alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(0);
    });

    it('should auto-dismiss warning alerts after 5 seconds', () => {
      window.displayAlert('Warning message', 'warning');

      const container = document.getElementById('alert-container');
      let alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(1);

      // Fast-forward time by 5 seconds
      vi.advanceTimersByTime(5000);

      // Wait for animation to complete
      vi.advanceTimersByTime(300);

      alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(0);
    });

    it('should not auto-dismiss if manually closed before timeout', () => {
      window.displayAlert('Test message', 'success');

      const container = document.getElementById('alert-container');
      const closeBtn = container.querySelector('.alert-close');

      // Manually close the alert
      closeBtn.click();

      // Wait for animation
      vi.advanceTimersByTime(300);

      const alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(0);

      // Fast-forward to when auto-dismiss would have occurred
      vi.advanceTimersByTime(3000);

      // Should still be 0 (no errors from trying to remove already-removed element)
      expect(container.querySelectorAll('.alert').length).toBe(0);
    });
  });

  describe('Manual close functionality', () => {
    it('should remove alert when close button is clicked', () => {
      window.displayAlert('Test message', 'info');

      const container = document.getElementById('alert-container');
      let alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(1);

      const closeBtn = container.querySelector('.alert-close');
      closeBtn.click();

      // Wait for animation to complete
      vi.advanceTimersByTime(300);

      alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(0);
    });

    it('should apply fade-out animation when closing', () => {
      window.displayAlert('Test message', 'info');

      const container = document.getElementById('alert-container');
      const alert = container.querySelector('.alert');
      const closeBtn = alert.querySelector('.alert-close');

      closeBtn.click();

      // Check that fade-out styles are applied
      expect(alert.style.opacity).toBe('0');
      expect(alert.style.transform).toBe('translateX(100%)');
      expect(alert.style.transition).toContain('0.3s');
    });
  });

  describe('Multiple alerts', () => {
    it('should display multiple alerts simultaneously', () => {
      window.displayAlert('Message 1', 'success');
      window.displayAlert('Message 2', 'error');
      window.displayAlert('Message 3', 'warning');

      const container = document.getElementById('alert-container');
      const alerts = container.querySelectorAll('.alert');

      expect(alerts.length).toBe(3);
      expect(alerts[0].textContent).toContain('Message 1');
      expect(alerts[1].textContent).toContain('Message 2');
      expect(alerts[2].textContent).toContain('Message 3');
    });

    it('should stack alerts vertically with spacing', () => {
      window.displayAlert('Message 1', 'success');
      window.displayAlert('Message 2', 'error');

      const container = document.getElementById('alert-container');
      const alerts = container.querySelectorAll('.alert');

      alerts.forEach(alert => {
        expect(alert.className).toContain('mb-2');
      });
    });

    it('should auto-dismiss each alert independently', () => {
      window.displayAlert('Success', 'success');
      window.displayAlert('Error', 'error');

      const container = document.getElementById('alert-container');
      let alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(2);

      // Fast-forward 3 seconds - success should be removed
      vi.advanceTimersByTime(3000);
      vi.advanceTimersByTime(300); // Animation time

      alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(1);
      expect(alerts[0].textContent).toContain('Error');

      // Fast-forward another 2 seconds - error should be removed
      vi.advanceTimersByTime(2000);
      vi.advanceTimersByTime(300); // Animation time

      alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(0);
    });
  });

  describe('clearAllAlerts function', () => {
    it('should remove all alerts from the container', () => {
      window.displayAlert('Message 1', 'success');
      window.displayAlert('Message 2', 'error');
      window.displayAlert('Message 3', 'warning');

      const container = document.getElementById('alert-container');
      let alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(3);

      window.clearAllAlerts();

      alerts = container.querySelectorAll('.alert');
      expect(alerts.length).toBe(0);
    });

    it('should handle empty container gracefully', () => {
      expect(() => {
        window.clearAllAlerts();
      }).not.toThrow();

      const container = document.getElementById('alert-container');
      expect(container.innerHTML).toBe('');
    });
  });

  describe('User feedback consistency', () => {
    it('should display exactly one alert per operation', () => {
      // Requirement 14.8 - Specific validation error messages
      const container = document.getElementById('alert-container');

      // Simulate an operation that succeeds
      window.displayAlert('Operation completed successfully', 'success');
      expect(container.querySelectorAll('.alert').length).toBe(1);

      // Clear for next test
      window.clearAllAlerts();

      // Simulate an operation that fails
      window.displayAlert('Operation failed: Network error', 'error');
      expect(container.querySelectorAll('.alert').length).toBe(1);
    });

    it('should provide descriptive error messages', () => {
      // Requirement 14.1 - Error alert with description
      window.displayAlert('Failed to export CSV: Invalid data format', 'error');

      const container = document.getElementById('alert-container');
      const alert = container.querySelector('.alert');

      expect(alert.textContent).toContain('Failed to export CSV');
      expect(alert.textContent).toContain('Invalid data format');
    });

    it('should provide specific validation error messages', () => {
      // Requirement 14.8 - Specific validation error messages
      window.displayAlert('Validation failed: Email field is required', 'error');

      const container = document.getElementById('alert-container');
      const alert = container.querySelector('.alert');

      expect(alert.textContent).toContain('Validation failed');
      expect(alert.textContent).toContain('Email field is required');
    });
  });
});
