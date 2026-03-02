// Content script for AI Document Processing extension

console.log('AI Document Processing content script loaded');

// Listen for messages from popup or background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getDocument') {
    // Extract document from current page
    sendResponse({ document: document.body.innerText });
  }
});
