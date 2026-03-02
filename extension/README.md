# AI Document Processing Browser Extension

Chrome/Edge compatible browser extension for extracting structured data from unstructured documents using AWS AI services.

## Structure

```
extension/
├── manifest.json          # Extension manifest (Manifest V3)
├── popup.html            # Main popup UI with 5 tabs
├── background.js         # Background service worker
├── content.js           # Content script
├── package.json         # NPM dependencies
├── tailwind.config.js   # Tailwind CSS configuration
├── vitest.config.js     # Vitest test configuration
├── icons/               # Extension icons
│   └── README.md
├── scripts/             # JavaScript modules
│   ├── popup.js        # Main popup script with tab navigation
│   └── storage.js      # Local Storage utility with encryption
└── styles/              # CSS files
    ├── tailwind.css    # Tailwind input
    └── output.css      # Tailwind output (generated)
```

## Features Implemented

### Task 11.1: Manifest Configuration ✓
- **Manifest Version**: 3 (Chrome/Edge compatible)
- **Permissions**: storage, tabs, downloads, clipboardWrite
- **Content Security Policy**: Configured for extension pages
- **Icons**: Placeholder structure for 16x16, 48x48, 128x128
- **Background**: Service worker configured
- **Content Scripts**: Configured for all URLs

### Task 11.2: Popup HTML Structure ✓
- **5 Tabs**: Dashboard, Prompts/Datapoints, Settings, Profile, Admin
- **Black & White Theme**: Headers and navigation use black/white colors
- **Tailwind CSS**: Applied throughout for styling
- **Dashboard Tab**:
  - Process Document button
  - Select Prompt dropdown
  - RESULT section with editable table
  - ACTION section with 7 circular icon buttons
  - METADATA section (collapsible)
  - HISTORY section (collapsible with pagination)
- **Alert Container**: For success/error/warning messages
- **Loading Overlay**: Spinner for async operations

### Task 11.3: Local Storage Utility ✓
- **StorageManager Class**: Singleton pattern
- **Chrome Storage API**: Wrapper for chrome.storage.local
- **Encryption/Decryption**: XOR cipher for sensitive credentials
  - FTP passwords
  - SMTP passwords
- **Specialized Methods**:
  - Session management (setSession, getSession, clearSession)
  - Prompts caching (setPrompts, getPrompts)
  - Settings storage (FTP, Email, API)
  - Results storage (setCurrentResults, getCurrentResults)
- **Error Handling**: Try-catch with proper error messages

## Requirements Validated

- **Requirement 17.1**: Chrome browser compatibility ✓
- **Requirement 17.2**: Edge browser compatibility ✓
- **Requirement 17.3**: Necessary browser permissions declared ✓
- **Requirement 17.4**: Chrome/Edge storage API usage ✓
- **Requirement 17.7**: Chrome Web Store guidelines followed ✓
- **Requirement 16.1**: Black and white theme for headers ✓
- **Requirement 16.2**: Colored buttons for visual distinction ✓
- **Requirement 16.3**: Tailwind CSS styling ✓
- **Requirement 16.4**: Consistent table formatting ✓
- **Requirement 13.2**: Credential encryption in Local Storage ✓

## Installation

1. Install dependencies:
```bash
npm install
```

2. Build Tailwind CSS:
```bash
npm run build:css
```

3. Load extension in Chrome/Edge:
   - Open `chrome://extensions/` (or `edge://extensions/`)
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `extension` directory

## Development

### Watch CSS Changes
```bash
npm run watch:css
```

### Run Tests
```bash
npm test
```

## Dependencies

### Production
- **papaparse**: CSV parsing and generation
- **xlsx**: XLSX file generation

### Development
- **tailwindcss**: Utility-first CSS framework
- **fast-check**: Property-based testing
- **vitest**: Unit testing framework

## Security

- Passwords and sensitive credentials are encrypted before storage
- XOR cipher with base64 encoding (production should use Web Crypto API with AES-GCM)
- Session tokens stored securely in Chrome storage
- Content Security Policy prevents inline scripts

## Next Steps

The following components need to be implemented:
- API client module for backend communication
- Dashboard tab functionality (document processing)
- Prompts/Datapoints tab functionality
- Settings tab functionality
- Profile tab functionality (authentication)
- Admin tab functionality
- Action buttons (export, FTP, email, API)
- Integration with AWS backend services

## Notes

- Icons need to be created (16x16, 48x48, 128x128 PNG files)
- SMTP functionality will use browser-based email sending (no smtp.js package)
- Admin tab is hidden by default and shown only for System Users
- All async operations show loading indicator
- Alerts auto-dismiss after 3 seconds for success messages
