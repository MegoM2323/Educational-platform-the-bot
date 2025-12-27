import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import "./i18n/i18n"; // Initialize i18n
import { registerServiceWorker } from "./services/serviceWorkerManager";

// Register service worker for offline functionality
registerServiceWorker().catch(error => {
  console.error("Failed to register service worker:", error);
});

createRoot(document.getElementById("root")!).render(<App />);
