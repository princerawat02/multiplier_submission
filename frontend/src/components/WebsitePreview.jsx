import React from "react";
import { API_BASE_URL } from "../config";

function getScreenshotUrl(screenshotPath) {
  if (!screenshotPath) {
    return "";
  }

  if (
    screenshotPath.startsWith("http://") ||
    screenshotPath.startsWith("https://")
  ) {
    return screenshotPath;
  }

  return `${API_BASE_URL}${screenshotPath}`;
}

export default function WebsitePreview({ website }) {
  const imageUrl = getScreenshotUrl(website.screenshot_path);

  return (
    <article className="website-card">
      <div className="website-image-wrap">
        <img
          src={imageUrl}
          alt={`Preview of ${website.url}`}
          className="website-image"
        />
      </div>
      <div className="website-content">
        <a
          href={website.url}
          target="_blank"
          rel="noreferrer"
          className="website-url"
        >
          {website.url}
        </a>
        <p className="website-date">
          Saved on {new Date(website.created_at).toLocaleString()}
        </p>
      </div>
    </article>
  );
}
