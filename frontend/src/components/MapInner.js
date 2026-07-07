"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";

// Leaflet assets URL configuration to avoid Next.js marker loading bugs
const markerIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// Component to dynamically pan and zoom the map when coordinates change
function MapRecenter({ lat, lng }) {
  const map = useMap();
  useEffect(() => {
    if (lat && lng) {
      map.setView([lat, lng], 13, { animate: true });
    }
  }, [lat, lng, map]);
  return null;
}

export default function MapInner({ latitude, longitude, estimation }) {
  const center = [latitude || 48.8566, longitude || 2.3522];

  return (
    <MapContainer 
      center={center} 
      zoom={13} 
      scrollWheelZoom={true} 
      style={{ width: "100%", height: "100%", minHeight: "400px" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <MapRecenter lat={latitude} lng={longitude} />
      {latitude && longitude && (
        <Marker position={[latitude, longitude]} icon={markerIcon}>
          <Popup>
            <div style={{ color: "#1e293b", fontSize: "0.85rem", lineHeight: "1.4" }}>
              <strong style={{ fontSize: "0.9rem" }}>📍 Secteur {estimation?.code_postal}</strong>
              <br />
              <b>Type :</b> {estimation?.type_bien}
              <br />
              <b>Caractéristiques :</b> {estimation?.surface_m2}m² — {estimation?.nb_pieces}p
              <br />
              <strong style={{ color: "var(--accent-primary)", display: "block", marginTop: "0.25rem" }}>
                Valeur : {new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(estimation?.prix_estime)}
              </strong>
            </div>
          </Popup>
        </Marker>
      )}
    </MapContainer>
  );
}
