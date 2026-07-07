"use client";

import { useState, useEffect } from "react";
import EstimationForm from "@/components/EstimationForm";
import EstimationResult from "@/components/EstimationResult";
import InteractiveMap from "@/components/InteractiveMap";
import Chatbot from "@/components/Chatbot";

export default function Home() {
  const [activeTab, setActiveTab] = useState("estimate");
  const [estimation, setEstimation] = useState(null);
  const [loadingEstimate, setLoadingEstimate] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [apiOnline, setApiOnline] = useState("checking"); // 'checking' | 'online' | 'offline'

  const BACKEND_URL = "http://localhost:8000";

  // Check FastAPI backend server connectivity on mount
  const checkApiStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/`);
      if (res.ok) {
        setApiOnline("online");
      } else {
        setApiOnline("offline");
      }
    } catch (err) {
      setApiOnline("offline");
    }
  };

  useEffect(() => {
    checkApiStatus();
    // Periodically poll API status every 10 seconds to maintain status sync
    const interval = setInterval(checkApiStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleEstimateSubmit = async (formData) => {
    setLoadingEstimate(true);
    try {
      const res = await fetch(`${BACKEND_URL}/estimate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        throw new Error("Erreur serveur backend lors de la prédiction.");
      }

      const data = await res.json();
      setEstimation(data);
      setApiOnline("online");
    } catch (err) {
      alert("Erreur de connexion : " + err.message);
      setApiOnline("offline");
    } finally {
      setLoadingEstimate(false);
    }
  };

  const handleChatSubmit = async (message) => {
    setLoadingChat(true);
    try {
      const res = await fetch(`${BACKEND_URL}/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      if (!res.ok) {
        throw new Error("Erreur serveur lors du traitement du chat.");
      }

      const data = await res.json();
      setApiOnline("online");
      return data.response;
    } catch (err) {
      setApiOnline("offline");
      throw err;
    } finally {
      setLoadingChat(false);
    }
  };

  return (
    <div className="app-container">
      {/* Premium Header */}
      <header className="app-header glass-panel">
        <div className="logo-container">
          <div className="logo-icon">E</div>
          <span className="logo-text">EstimIA</span>
        </div>
        
        <div className="api-status">
          <span className={`status-dot ${apiOnline === "online" ? "online" : apiOnline === "offline" ? "offline" : ""}`}></span>
          <span>
            {apiOnline === "online" ? "Moteur IA connecté" : 
             apiOnline === "offline" ? "Moteur IA déconnecté" : "Vérification..."}
          </span>
        </div>
      </header>

      {/* Offline Warning Banner */}
      {apiOnline === "offline" && (
        <div className="offline-banner">
          <div className="offline-details">
            <span style={{ fontSize: "1.5rem" }}>⚠️</span>
            <div>
              <strong style={{ display: "block" }}>Serveur API EstimIA hors-ligne</strong>
              <span style={{ fontSize: "0.85rem", opacity: 0.9 }}>
                Le backend FastAPI doit être démarré pour calculer les estimations. Lancez la commande suivante dans votre terminal :
              </span>
              <code style={{ 
                display: "block", 
                background: "rgba(0,0,0,0.3)", 
                padding: "0.3rem 0.5rem", 
                borderRadius: "4px", 
                fontSize: "0.8rem",
                fontFamily: "monospace",
                marginTop: "0.4rem",
                color: "#ff7b72"
              }}>
                uvicorn main:app --reload --port 8000
              </code>
            </div>
          </div>
          <button className="offline-btn" onClick={checkApiStatus}>
            Réessayer 🔄
          </button>
        </div>
      )}

      {/* Tab Navigation */}
      <nav className="tabs-navigation">
        <button 
          className={`tab-btn ${activeTab === "estimate" ? "active" : ""}`}
          onClick={() => setActiveTab("estimate")}
        >
          📊 Calculateur d'Estimation
        </button>
        <button 
          className={`tab-btn ${activeTab === "chatbot" ? "active" : ""}`}
          onClick={() => setActiveTab("chatbot")}
        >
          💬 Geo-Estate AI Advisor
        </button>
      </nav>

      {/* Dynamic Tab Content */}
      <main className="main-content">
        {activeTab === "estimate" ? (
          <div className="main-content two-columns">
            {/* Form Column */}
            <div>
              <EstimationForm onSubmit={handleEstimateSubmit} loading={loadingEstimate} />
            </div>

            {/* Results & Maps Column */}
            <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              <EstimationResult estimation={estimation} />
              
              <div style={{ height: "400px" }}>
                <InteractiveMap 
                  latitude={estimation?.latitude} 
                  longitude={estimation?.longitude} 
                  estimation={estimation}
                />
              </div>
            </div>
          </div>
        ) : (
          <div>
            <Chatbot onSendMessage={handleChatSubmit} loading={loadingChat} />
          </div>
        )}
      </main>
    </div>
  );
}
