# Alert/Notification System Documentation

## Overview

The alert system provides consistent user feedback for all operations in the AI Document Processing extension. It displays success, error, warning, and info messages with automatic dismissal and manual close functionality.

## Requirements

This implementation satisfies the following requirements:
- **14.1**: Display error alerts with descriptions when API calls fail
- **14.2**: Display success alerts when API calls succeed
- **14.3**: Display warning alerts for document processing failures
- **14.8**: Display specific validation error messages

## Features

### Alert Types

1. **Success** (green)
   - Used for successful operations
   - Auto-dismisses after 3 seconds
   - Icon: ✓

2. **Error** (red)
   - Used for failed operations
   - Auto-dismisses after 5 seconds
   - Icon: ✕

3. **Warning** (yellow)
   - Used for validation issues or warnings
   - Auto-dismisses after 5 seconds
   - Icon: ⚠

4. **Info** (blue)
   - Used for general information
   - Auto-dismisses after 5 seconds
   - Icon: ℹ

### Key Features

- **Consistent Styling**: All alerts use Tailwind CSS with consistent spacing, colors, and layout
- **Auto-Dismiss**: Success alerts dismiss after 3 seconds, others after 5 seconds
- **Manual Close**: Users can close any alert by clicking the × button
- **Animations**: Smooth slide-in and fade-out animations
- **XSS Protection**: All messages are HTML-escaped to prevent injection attacks
- **Multiple Alerts**: Supports displaying multiple alerts simultaneously
- **Responsive**: Alerts stack vertically with proper spacing

## Usage

### Basic Usage

```javascript
// Success alert
displayAlert('Operation completed successfully!', 'success');

// Error alert
displayAlert('Failed to process document: Network error', 'error');

// Warning alert
displayAlert('No data available to export', 'warning');

// Info alert (default)
displayAlert('Loading data...', 'info');
// or simply
displayAlert('Loading data...');
```

### Integration Examples

#### CSV Export
```javascript
function exportToCSV(data) {
  try {
    if (!data || Object.keys(data).length === 0) {
      displayAlert('No data available to export', 'warning');
      return;
    }
    
    // Export logic...
    displayAlert('CSV file downloaded successfully!', 'success');
  } catch (error) {
    displayAlert(`Failed to export CSV: ${error.message}`, 'error');
  }
}
```

#### API Calls
```javascript
async function processDocument() {
  try {
    const response = await apiClient.processDocument(data);
    displayAlert('Document processed successfully!', 'success');
    return response;
  } catch (error) {
    displayAlert(`Failed to process document: ${error.message}`, 'error');
    throw error;
  }
}
```

#### Form Validation
```javascript
function validateForm(formData) {
  if (!formData.email) {
    displayAlert('Validation failed: Email field is required', 'error');
    return false;
  }
  return true;
}
```

#### Settings Save
```javascript
function saveSettings(settings) {
  try {
    localStorage.setItem('settings', JSON.stringify(settings));
    displayAlert('Settings saved successfully!', 'success');
  } catch (error) {
    displayAlert(`Failed to save settings: ${error.message}`, 'error');
  }
}
```

### Advanced Usage

#### Clear All Alerts
```javascript
// Remove all alerts from the screen
clearAllAlerts();
```

#### Manual Alert Removal
```javascript
// Alerts can be manually closed by users clicking the × button
// Or programmatically using removeAlert(alertElement)
```

## HTML Structure

The alert system requires an alert container in your HTML:

```html
<div id="alert-container" class="fixed top-4 right-4 z-50 space-y-2"></div>
```

This container is already included in `popup.html`.

## CSS Requirements

The alert system uses Tailwind CSS classes and custom animations defined in `styles/tailwind.css`:

```css
@keyframes slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.animate-slide-in {
  animation: slide-in 0.3s ease-out;
}
```

## Script Loading

Include the alerts script in your HTML before other scripts that use it:

```html
<script src="scripts/alerts.js"></script>
<script src="scripts/dashboard.js"></script>
<script src="scripts/prompts.js"></script>
<!-- other scripts -->
```

## Testing

The alert system includes comprehensive unit tests in `tests/alerts.test.js`:

- Display alerts of all types
- Auto-dismiss functionality
- Manual close functionality
- Multiple alerts handling
- XSS protection
- Error handling

Run tests with:
```bash
npm test -- alerts.test.js
```

## API Reference

### displayAlert(message, type)

Displays an alert message to the user.

**Parameters:**
- `message` (string): The message to display
- `type` (string, optional): Alert type - 'success', 'error', 'warning', or 'info' (default: 'info')

**Returns:** void

**Example:**
```javascript
displayAlert('Operation successful', 'success');
```

### removeAlert(alert)

Removes a specific alert element with fade-out animation.

**Parameters:**
- `alert` (HTMLElement): The alert element to remove

**Returns:** void

### clearAllAlerts()

Removes all alerts from the container immediately.

**Returns:** void

**Example:**
```javascript
clearAllAlerts();
```

## Best Practices

1. **Be Specific**: Provide clear, actionable messages
   ```javascript
   // Good
   displayAlert('Failed to export CSV: Invalid data format', 'error');
   
   // Bad
   displayAlert('Error', 'error');
   ```

2. **Use Appropriate Types**: Match the alert type to the situation
   - Success: Operation completed successfully
   - Error: Operation failed or exception occurred
   - Warning: Validation issue or cautionary message
   - Info: General information or status updates

3. **Include Context**: Help users understand what happened
   ```javascript
   displayAlert(`Failed to connect to ${serverType}: ${error.message}`, 'error');
   ```

4. **Don't Overuse**: Avoid showing alerts for every minor action
   - Do show: Save success, API failures, validation errors
   - Don't show: Every button click, hover actions

5. **Handle Errors Gracefully**: Always catch and display errors
   ```javascript
   try {
     await riskyOperation();
     displayAlert('Success!', 'success');
   } catch (error) {
     displayAlert(`Operation failed: ${error.message}`, 'error');
   }
   ```

## Accessibility

- All alerts include ARIA labels for screen readers
- Close buttons have `aria-label="Close"` attributes
- Color is not the only indicator (icons are also used)
- Alerts are keyboard accessible

## Browser Compatibility

The alert system is compatible with:
- Chrome (latest)
- Edge (latest)
- All modern browsers supporting ES6+

## Troubleshooting

### Alerts Not Appearing

1. Check that `alert-container` div exists in HTML
2. Verify `alerts.js` is loaded before calling `displayAlert`
3. Check browser console for errors

### Styling Issues

1. Ensure Tailwind CSS is properly built: `npm run build:css`
2. Verify `output.css` includes the custom animations
3. Check that `output.css` is linked in HTML

### Auto-Dismiss Not Working

1. Verify JavaScript timers are not being blocked
2. Check that the alert element hasn't been manually removed
3. Ensure no errors in browser console

## Future Enhancements

Potential improvements for future versions:
- Configurable auto-dismiss timeouts
- Alert positioning options (top-left, bottom-right, etc.)
- Sound notifications
- Alert history/log
- Grouped alerts for similar messages
- Progress indicators for long operations
