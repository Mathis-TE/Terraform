"use client";

import { useState } from "react";

export default function EstimationForm({ onSubmit, loading }) {
  const [formData, setFormData] = useState({
    surface: "",
    pieces: "",
    code_postal: "",
    type_bien: "Appartement",
    annee_visite: 2025,
  });

  const [error, setError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "surface" || name === "pieces" ? value : value,
    }));
    setError("");
  };

  const handleTypeChange = (type) => {
    setFormData((prev) => ({
      ...prev,
      type_bien: type,
    }));
    setError("");
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Validations
    const surfaceNum = parseFloat(formData.surface);
    const piecesNum = parseInt(formData.pieces, 10);
    const cp = formData.code_postal.trim();

    if (isNaN(surfaceNum) || surfaceNum < 10 || surfaceNum > 300) {
      setError("La surface doit être un nombre compris entre 10 et 300 m².");
      return;
    }

    if (isNaN(piecesNum) || piecesNum < 1 || piecesNum > 10) {
      setError("Le nombre de pièces doit être compris entre 1 et 10.");
      return;
    }

    if (!/^\d{5}$/.test(cp)) {
      setError("Le code postal doit contenir exactement 5 chiffres.");
      return;
    }

    const validIDF = /^(75|77|78|91|92|93|94|95)\d{3}$/.test(cp);
    if (!validIDF) {
      setError("Le code postal doit être situé en Île-de-France (75, 77, 78, 91-95).");
      return;
    }

    onSubmit({
      surface: surfaceNum,
      pieces: piecesNum,
      code_postal: cp,
      type_bien: formData.type_bien,
      annee_visite: parseInt(formData.annee_visite, 10),
    });
  };

  return (
    <form className="glass-panel" style={{ padding: "1.5rem" }} onSubmit={handleSubmit}>
      <h2 className="form-title">Critères du Bien</h2>

      {error && (
        <div style={{
          background: "rgba(239, 68, 68, 0.1)",
          border: "1px solid var(--danger)",
          color: "var(--danger)",
          padding: "0.75rem",
          borderRadius: "8px",
          fontSize: "0.85rem",
          marginBottom: "1rem"
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Type de bien toggle */}
      <div className="form-group">
        <span className="form-label">Type de propriété</span>
        <div className="toggle-group">
          <div className="toggle-option">
            <input
              type="radio"
              id="type-appt"
              name="type_bien"
              checked={formData.type_bien === "Appartement"}
              onChange={() => handleTypeChange("Appartement")}
            />
            <label htmlFor="type-appt" className="toggle-label">🏢 Appartement</label>
          </div>
          <div className="toggle-option">
            <input
              type="radio"
              id="type-maison"
              name="type_bien"
              checked={formData.type_bien === "Maison"}
              onChange={() => handleTypeChange("Maison")}
            />
            <label htmlFor="type-maison" className="toggle-label">🏡 Maison</label>
          </div>
        </div>
      </div>

      {/* Surface input */}
      <div className="form-group">
        <label className="form-label" htmlFor="surface">Surface habitable (m²)</label>
        <div className="input-wrapper">
          <input
            type="number"
            id="surface"
            name="surface"
            className="form-input"
            placeholder="Ex: 65"
            min="10"
            max="300"
            step="any"
            value={formData.surface}
            onChange={handleChange}
            required
          />
        </div>
      </div>

      {/* Pieces input */}
      <div className="form-group">
        <label className="form-label" htmlFor="pieces">Nombre de pièces</label>
        <input
          type="number"
          id="pieces"
          name="pieces"
          className="form-input"
          placeholder="Ex: 3"
          min="1"
          max="10"
          value={formData.pieces}
          onChange={handleChange}
          required
        />
      </div>

      {/* Code postal input */}
      <div className="form-group">
        <label className="form-label" htmlFor="code_postal">Code Postal (Île-de-France)</label>
        <input
          type="text"
          id="code_postal"
          name="code_postal"
          className="form-input"
          placeholder="Ex: 92100"
          maxLength={5}
          value={formData.code_postal}
          onChange={handleChange}
          required
        />
      </div>

      {/* Année select */}
      <div className="form-group">
        <label className="form-label" htmlFor="annee_visite">Année de référence</label>
        <select
          id="annee_visite"
          name="annee_visite"
          className="form-select"
          value={formData.annee_visite}
          onChange={handleChange}
        >
          <option value={2025}>2025 (Actuelle)</option>
          <option value={2026}>2026</option>
          <option value={2027}>2027</option>
        </select>
      </div>

      <button type="submit" className="submit-btn" disabled={loading}>
        {loading ? (
          <>
            <div className="typing-indicator" style={{ padding: 0 }}>
              <div className="typing-dot" style={{ backgroundColor: "#fff" }}></div>
              <div className="typing-dot" style={{ backgroundColor: "#fff" }}></div>
              <div className="typing-dot" style={{ backgroundColor: "#fff" }}></div>
            </div>
            <span>Calcul en cours...</span>
          </>
        ) : (
          <>
            <span>⚡ Estimer la valeur</span>
          </>
        )}
      </button>
    </form>
  );
}
