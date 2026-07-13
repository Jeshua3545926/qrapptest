const configuredBase = import.meta.env.VITE_API_BASE?.trim() || ''

export const API_BASE = (() => {
  // If configured, use it
  if (configuredBase) {
    return configuredBase
  }

  // Check if running on Render production
  if (window.location.hostname.includes('onrender.com') || 
      window.location.hostname.includes('render.com')) {
    return 'https://qrapptest.onrender.com'
  }

  // Otherwise, use the backend on the same host but port 5000
  return `${window.location.protocol}//${window.location.hostname}:5000`
})()
