"use client";

import { useState, useRef, useEffect } from "react";

export default function Chatbot({ onSendMessage, loading }) {
  const [messages, setMessages] = useState([
    {
      sender: "assistant",
      text: "Bonjour ! Je suis **Geo-Estate AI**, votre expert d'estimation immobilière en Île-de-France.\n\nJe peux estimer instantanément n'importe quel bien de la région grâce à nos algorithmes de Machine Learning et nos indicateurs de risques enrichis.\n\nPour produire votre rapport d'estimation, veuillez m'indiquer :\n1. La **surface habitable** en m²\n2. Le **nombre de pièces** principales\n3. Le **code postal** à 5 chiffres (ex: 92100, 75015)\n4. Le **type de bien** (*Maison* ou *Appartement*)\n\nExemple : *\"Estime un appartement de 65m2 avec 3 pièces à Boulogne 92100\"*"
    }
  ]);
  const [inputText, setInputText] = useState("");
  const chatHistoryRef = useRef(null);

  const suggestionChips = [
    "Appartement 65m² 3p à Boulogne 92100",
    "Maison 120m² 5p à Versailles 78000",
    "Appartement 30m² 1p à Paris 75005"
  ];

  // Auto-scroll chat to the bottom when messages or loading state changes
  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    const text = textToSend || inputText.trim();
    if (!text) return;

    if (!textToSend) setInputText("");

    // Add user message to state
    setMessages((prev) => [...prev, { sender: "user", text }]);

    try {
      // Trigger the backend API query passed from parent page
      const response = await onSendMessage(text);
      setMessages((prev) => [...prev, { sender: "assistant", text: response }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "assistant",
          text: "Désolé, j'ai rencontré un problème pour me connecter au serveur backend. Veuillez vérifier que l'API FastAPI est bien lancée sur le port 8000."
        }
      ]);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Safe and lightweight regex-based formatter for chat assistant replies
  const renderMessageContent = (text) => {
    let html = text;

    // Escape basic HTML to prevent XSS
    html = html
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Headings (### title)
    html = html.replace(/^### (.*?)$/gm, "<h3>$1</h3>");

    // Bullet points with bold titles (* **Title** : Value)
    html = html.replace(/^\* \*\*(.*?)\*\* : (.*?)$/gm, "<li><strong>$1</strong> : $2</li>");
    
    // Simple bullet points (* text)
    html = html.replace(/^\* (.*?)$/gm, "<li>$1</li>");

    // Wrap adjacent list items in a ul (rough parser)
    html = html.replace(/(<li>.*?<\/li>)+/g, "<ul>$&</ul>");

    // Bold text (**text**)
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Italic text (*text*)
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Line breaks
    html = html.replace(/\n/g, "<br />");

    return <div dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <div className="glass-panel chatbot-container">
      {/* Scrollable Message History */}
      <div className="chat-history" ref={chatHistoryRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`chat-message ${msg.sender}`}>
            {renderMessageContent(msg.text)}
          </div>
        ))}

        {loading && (
          <div className="chat-message assistant">
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        )}
      </div>

      {/* Suggestion Chips */}
      <div className="chat-chips-container">
        {suggestionChips.map((chip, idx) => (
          <button
            key={idx}
            className="chip-btn"
            onClick={() => handleSend(chip)}
            disabled={loading}
          >
            💬 {chip}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="chat-input-area">
        <input
          type="text"
          className="chat-input"
          placeholder="Posez votre question (ex: Estime un appartement de 70m2...)"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={() => handleSend()}
          disabled={loading || !inputText.trim()}
        >
          ✈️
        </button>
      </div>
    </div>
  );
}
