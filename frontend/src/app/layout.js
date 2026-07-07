import "./globals.css";

export const metadata = {
  title: "EstimIA — L'estimation immobilière augmentée en Île-de-France",
  description: "Rapports d'estimation complets, précis et professionnels en temps réel pour l'Île-de-France, couplés avec l'intelligence de Geo-Estate AI.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <head>
        {/* Leaflet CSS CDN for Map Component */}
        <link 
          rel="stylesheet" 
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
