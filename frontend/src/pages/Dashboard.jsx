import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import WebsitePreview from "../components/WebsitePreview";
import { API_BASE_URL } from "../config";

const TEST_URL =
  "";

export default function Dashboard() {
  const navigate = useNavigate();
  const [url, setUrl] = useState(TEST_URL);
  const [websites, setWebsites] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchWebsites();
  }, []);

  async function fetchWebsites() {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    setLoadingList(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/websites`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to load websites.");
      }

      setWebsites(data);
    } catch (fetchError) {
      setError(fetchError.message);
    } finally {
      setLoadingList(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const token = localStorage.getItem("token");

    if (!token) {
      navigate("/login");
      return;
    }

    if (!url.trim()) {
      setError("Please enter a website URL.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/preview`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ url }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not generate preview.");
      }

      setWebsites((prev) => [data, ...prev]);
      setUrl("");
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <h1>Website Preview App</h1>
          <p>Welcome! Submit a URL to capture and save a website preview.</p>
        </div>
        <button onClick={handleLogout} className="secondary-btn">
          Logout
        </button>
      </header>

      <section className="submit-section">
        <form onSubmit={handleSubmit} className="submit-form">
          <input
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://example.com"
          />
          <button className="primary-btn" type="submit" disabled={submitting}>
            {submitting ? "Generating preview..." : "Submit"}
          </button>
        </form>
        {error && <p className="message error">{error}</p>}
      </section>

      <section className="saved-section">
        <h2>Saved Websites</h2>
        {loadingList ? (
          <p className="message">Loading saved websites...</p>
        ) : null}
        {!loadingList && websites.length === 0 ? (
          <p className="message">No websites saved yet.</p>
        ) : null}
        <div className="website-grid">
          {websites.map((website) => (
            <WebsitePreview key={website.id} website={website} />
          ))}
        </div>
      </section>
    </main>
  );
}
