/**
 * AI-SENTRY -- React Entry Point
 * main.tsx
 *
 * Mounts the React application into the DOM.
 * This file is loaded by the Electron renderer process.
 */

import React from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error(
    "Root element not found. Ensure index.html has a <div id='root'></div>."
  );
}

const root = createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
