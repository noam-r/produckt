import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Performance measurement
const startTime = performance.now();
console.log('[Performance] main.jsx executed at:', startTime.toFixed(2), 'ms');

// Hide the initial HTML loader once React starts rendering
const initialLoader = document.getElementById('initial-loader');
if (initialLoader) {
  initialLoader.classList.add('hidden');
  console.log('[Performance] HTML loader hidden at:', (performance.now() - startTime).toFixed(2), 'ms');
}

// Disable StrictMode in development for better performance
// StrictMode causes double-rendering which can amplify delays
// Re-enable for production builds
createRoot(document.getElementById('root')).render(<App />)

console.log('[Performance] React render initiated at:', (performance.now() - startTime).toFixed(2), 'ms');
