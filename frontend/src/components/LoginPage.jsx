// components/LoginPage.jsx
// Modern, beginner-friendly Login screen with instant demo login.

import { useState } from "react";
import { loginUser } from "../services/api";

export default function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    if (e) e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Please enter both username and password.");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      const data = await loginUser(username.trim(), password.trim());
      onLoginSuccess({
        username: data.username,
        token: data.token,
      });
    } catch (err) {
      setError(err.message || "Failed to log in. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleDemoLogin() {
    setUsername("admin");
    setPassword("admin123");
    setError(null);
    setIsLoading(true);
    loginUser("admin", "admin123")
      .then((data) => {
        onLoginSuccess({
          username: data.username,
          token: data.token,
        });
      })
      .catch((err) => {
        setError(err.message || "Demo login failed.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Brand header */}
        <div className="login-brand">
          <span className="login-logo">🤖</span>
          <h1 className="login-title">Lexi AI</h1>
          <p className="login-subtitle">Context-Aware AI Learning Assistant</p>
        </div>

        {/* Error notification */}
        {error && (
          <div className="login-error" role="alert">
            <span>⚠️ {error}</span>
          </div>
        )}

        {/* Form */}
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. admin or your name"
              autoFocus
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            className="login-submit-btn"
            disabled={isLoading || !username || !password}
          >
            {isLoading ? "Signing in…" : "Sign In →"}
          </button>
        </form>

        {/* Demo login shortcut */}
        <div className="demo-login-box">
          <div className="demo-login-text">
            <span>Want to test quickly without typing?</span>
          </div>
          <button
            type="button"
            className="demo-btn"
            onClick={handleDemoLogin}
            disabled={isLoading}
          >
            ⚡ One-Click Demo Sign In (admin)
          </button>
        </div>

        <div className="login-footer">
          <span className="feature-pill">🧠 10-turn memory</span>
          <span className="feature-pill">📂 Sidebar history</span>
          <span className="feature-pill">⚡ Gemini 3.5 Flash Lite</span>
        </div>
      </div>
    </div>
  );
}

