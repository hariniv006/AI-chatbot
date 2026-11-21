// main.jsx
// The entry point for the React application.
// It mounts the root <App /> component into the #root div in index.html.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

// StrictMode intentionally renders components twice in development to help
// detect side-effects that should not run on every render.  It has no effect
// in production builds.
createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);

