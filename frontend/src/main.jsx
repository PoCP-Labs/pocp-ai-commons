import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import App from "./App.jsx";
import ErrorBoundary from "./ErrorBoundary.jsx";
import { I18nProvider } from "./i18n/index.jsx";

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("#root element missing");
}

createRoot(rootEl).render(
  <StrictMode>
    <ErrorBoundary>
      <I18nProvider>
        <App />
      </I18nProvider>
    </ErrorBoundary>
  </StrictMode>
);
