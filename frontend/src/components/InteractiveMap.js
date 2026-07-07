"use client";

import dynamic from "next/dynamic";

// Dynamically import the Leaflet map component with ssr: false to prevent Next.js compilation issues
const DynamicMapInner = dynamic(
  () => import("./MapInner"),
  { 
    ssr: false,
    loading: () => (
      <div className="svg-map-fallback">
        <div className="typing-indicator" style={{ marginBottom: "1rem" }}>
          <div className="typing-dot"></div>
          <div className="typing-dot"></div>
          <div className="typing-dot"></div>
        </div>
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          Chargement de la carte interactive...
        </p>
      </div>
    )
  }
);

export default function InteractiveMap({ latitude, longitude, estimation }) {
  return (
    <div className="map-container-wrapper">
      {!latitude || !longitude ? (
        <div className="svg-map-fallback">
          <svg width="100" height="100" viewBox="0 0 100 100" style={{ marginBottom: "1rem" }}>
            <circle cx="50" cy="50" r="16" fill="rgba(99, 102, 241, 0.15)" stroke="var(--accent-primary)" strokeWidth="2" />
            <circle className="svg-map-circle" cx="50" cy="50" r="24" fill="none" stroke="var(--accent-primary)" strokeWidth="1.5" />
            <circle cx="50" cy="50" r="4" fill="var(--accent-primary)" />
          </svg>
          <h3>Localisation géographique</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "0.5rem", maxWidth: "250px" }}>
            La carte s'affichera et se centrera sur la zone du bien dès qu'une estimation sera calculée.
          </p>
        </div>
      ) : (
        <DynamicMapInner 
          latitude={latitude} 
          longitude={longitude} 
          estimation={estimation} 
        />
      )}
    </div>
  );
}
