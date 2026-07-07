"use client";

import { useEffect, useState } from "react";

export default function EstimationResult({ estimation }) {
  const [animatedPrice, setAnimatedPrice] = useState(0);

  // Smooth price count-up animation when estimation changes
  useEffect(() => {
    if (!estimation || !estimation.prix_estime) return;
    
    const target = estimation.prix_estime;
    const duration = 800; // ms
    const stepTime = 16; // ~60fps
    const steps = duration / stepTime;
    const increment = target / steps;
    
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        setAnimatedPrice(target);
        clearInterval(timer);
      } else {
        setAnimatedPrice(Math.round(current));
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [estimation]);

  if (!estimation) {
    return (
      <div className="glass-panel" style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "3rem",
        height: "100%",
        minHeight: "450px",
        textAlign: "center",
        color: "var(--text-secondary)"
      }}>
        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>📊</div>
        <h3>En attente de saisie</h3>
        <p style={{ fontSize: "0.9rem", marginTop: "0.5rem", maxWidth: "280px" }}>
          Remplissez le formulaire à gauche pour lancer le modèle d'estimation statistique en temps réel.
        </p>
      </div>
    );
  }

  const formatEuro = (val) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0
    }).format(val);
  };

  const pricePerSqm = estimation.prix_estime / estimation.surface_m2;
  const georisquesColor = estimation.score_georisques > 7 ? "var(--danger)" : estimation.score_georisques > 4 ? "var(--warning)" : "var(--success)";
  const delinquanceColor = estimation.score_delinquance > 7 ? "var(--danger)" : estimation.score_delinquance > 4 ? "var(--warning)" : "var(--success)";

  return (
    <div className="glass-panel" style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Price Header Section */}
      <div className="result-header">
        <h3 className="result-subtitle">Valeur estimée du bien</h3>
        <div className="result-price">
          {formatEuro(animatedPrice)}
        </div>
        <div className="result-price-sqm">
          📈 {formatEuro(pricePerSqm)} / m²
        </div>
      </div>

      {/* Micro-Local Indicators Section */}
      <div style={{ padding: "1.5rem 1.5rem 0.5rem" }}>
        <h4 style={{ fontSize: "0.95rem", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
          📍 Indices micro-locaux du secteur
        </h4>
      </div>
      
      <div className="indicators-grid">
        {/* DPE Indicator */}
        <div className="indicator-card">
          <span className="indicator-title">Diagnostic DPE</span>
          <div className={`dpe-badge dpe-${estimation.classe_dpe}`}>
            {estimation.classe_dpe}
          </div>
          <span className="indicator-subtitle">Classe énergétique</span>
        </div>

        {/* Georisques Indicator */}
        <div className="indicator-card">
          <span className="indicator-title">Géorisques</span>
          <div className="indicator-score" style={{ color: georisquesColor }}>
            {estimation.score_georisques.toFixed(1)}<span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>/10</span>
          </div>
          <div className="progress-bar-container">
            <div 
              className="progress-bar-fill" 
              style={{ width: `${estimation.score_georisques * 10}%`, backgroundColor: georisquesColor }}
            ></div>
          </div>
          <span className="indicator-subtitle">
            {estimation.score_georisques > 6 ? "Risques élevés" : estimation.score_georisques > 3 ? "Risques modérés" : "Risques faibles"}
          </span>
        </div>

        {/* Delinquency Indicator */}
        <div className="indicator-card">
          <span className="indicator-title">Sécurité publique</span>
          <div className="indicator-score" style={{ color: delinquanceColor }}>
            {estimation.score_delinquance.toFixed(1)}<span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>/10</span>
          </div>
          <div className="progress-bar-container">
            <div 
              className="progress-bar-fill" 
              style={{ width: `${estimation.score_delinquance * 10}%`, backgroundColor: delinquanceColor }}
            ></div>
          </div>
          <span className="indicator-subtitle">
            {estimation.score_delinquance > 6 ? "Criminalité forte" : estimation.score_delinquance > 3 ? "Moyenne" : "Sûr"}
          </span>
        </div>
      </div>

      {/* Model Resolution Metadata */}
      <div className="metadata-section" style={{ marginTop: "auto" }}>
        <div className="metadata-grid">
          <div>
            <div className="metadata-item">Type de bien</div>
            <div className="metadata-value">{estimation.type_bien}</div>
          </div>
          <div>
            <div className="metadata-item">Caractéristiques</div>
            <div className="metadata-value">{estimation.surface_m2} m² — {estimation.nb_pieces} pièce(s)</div>
          </div>
          <div>
            <div className="metadata-item">Département</div>
            <div className="metadata-value">{estimation.departement} (Île-de-France)</div>
          </div>
          <div>
            <div className="metadata-item">Résolution spatiale</div>
            <div className="metadata-value" style={{ textTransform: "capitalize" }}>
              {estimation.source_resolution.replace("_", " ")}
            </div>
          </div>
          <div style={{ gridColumn: "span 2", marginTop: "0.25rem", borderTop: "1px solid rgba(255, 255, 255, 0.05)", paddingTop: "0.5rem" }}>
            <div className="metadata-item">Coordonnées de calcul (Latitude, Longitude)</div>
            <div className="metadata-value" style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--accent-primary)" }}>
              {estimation.latitude.toFixed(5)}, {estimation.longitude.toFixed(5)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
