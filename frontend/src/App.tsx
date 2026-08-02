import { useTheme } from "./hooks/useTheme";

// Two routes total ("/" and "/s/:sessionId"), and the app is a plain
// client-rendered SPA with no SSR/data-router needs - not enough surface
// to justify a router dependency. Hand-rolling this also sidesteps
// react-router's current advisory list, which as of writing spans nearly
// its entire published version range (mostly SSR/RSC/data-router issues
// that wouldn't even apply to how we'd use it, but there's no version to
// pin that avoids all of them).
function getSessionIdFromPath(): string | null {
  const match = window.location.pathname.match(/^\/s\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const sessionId = getSessionIdFromPath();

  return (
    <div className="page">
      <header className="header">
        <a className="logo" href="/">
          shhecrets
        </a>
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
          {theme === "dark" ? "☀" : "☾"}
        </button>
      </header>
      <main className="main">
        {sessionId ? (
          <p className="muted">view page lands in the next PR (session: {sessionId})</p>
        ) : (
          <p className="muted">create page lands in the next PR</p>
        )}
      </main>
    </div>
  );
}
