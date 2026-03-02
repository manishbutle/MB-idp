// Background service worker for AI Document Processing extension

chrome.runtime.onInstalled.addListener(() => {
  console.log('AI Document Processing extension installed');
});

// Handle extension icon click to open sidebar
chrome.action.onClicked.addListener((tab) => {
  // Open the side panel for Chrome
  if (chrome.sidePanel) {
    chrome.sidePanel.open({ windowId: tab.windowId });
  }
});

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Message received:', request);
  sendResponse({ status: 'received' });
});
