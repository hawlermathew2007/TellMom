import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Dashboard.css';
import ChatPanel from '../components/ChatPanel';
import RiskAssessmentPanel from '../components/RiskAssessmentPanel';
import AlertNotification from '../components/AlertNotification';

const Dashboard = ({ childId, onLogout }) => {
  const [messages, setMessages] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ws, setWs] = useState(null);
  const [riskSummary, setRiskSummary] = useState(null);

  // Fetch initial messages and setup WebSocket
  useEffect(() => {
    fetchMessages();
    fetchRiskSummary();
    setupWebSocket();

    return () => {
      if (ws) ws.close();
    };
  }, [childId]);

  const fetchMessages = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/messages/history?child_id=${childId}&limit=50`
      );
      setMessages(response.data.messages);
      // Auto-select first message
      if (response.data.messages.length > 0) {
        setSelectedMessage(response.data.messages[0]);
      }
    } catch (err) {
      console.error('Failed to fetch messages:', err);
    }
  };

  const fetchRiskSummary = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/messages/summary?child_id=${childId}`
      );
      setRiskSummary(response.data);
    } catch (err) {
      console.error('Failed to fetch risk summary:', err);
    }
  };

  const setupWebSocket = () => {
    try {
      const websocket = new WebSocket('ws://localhost:8000/api/alerts/ws/alerts');

      websocket.onopen = () => {
        console.log('[+] WebSocket connected');
      };

      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'alert') {
          // Add new alert
          setAlerts([data.data, ...alerts]);
          // Refresh messages
          fetchMessages();
          fetchRiskSummary();
        }
      };

      websocket.onerror = (error) => {
        console.error('[*] WebSocket error:', error);
      };

      setWs(websocket);
    } catch (err) {
      console.error('Failed to setup WebSocket:', err);
    }
  };

  const handleDeleteMessage = async (messageId) => {
    try {
      await axios.delete(`http://localhost:8000/api/messages/message/${messageId}`);
      setMessages(messages.filter((m) => m.id !== messageId));
      setSelectedMessage(null);
      alert('Message deleted successfully');
    } catch (err) {
      console.error('Failed to delete message:', err);
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      await axios.post(
        `http://localhost:8000/api/alerts/acknowledge/${alertId}?child_id=${childId}`
      );
      setAlerts(alerts.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a)));
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  return (
    <div className="dashboard">
      {/* Top Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1>🛡️ TellMom Dashboard</h1>
          <div className="header-stats">
            {riskSummary && (
              <>
                <div className="stat">
                  <span className="stat-label">Total Messages</span>
                  <span className="stat-value">{riskSummary.total_messages}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">🚨 Red Flags</span>
                  <span className="stat-value red">{riskSummary.red_flag_count}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">⚠️ Yellow Flags</span>
                  <span className="stat-value yellow">{riskSummary.yellow_flag_count}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Avg Risk</span>
                  <span className="stat-value">{(riskSummary.average_risk_score * 100).toFixed(1)}%</span>
                </div>
              </>
            )}
          </div>
          <button className="btn-logout" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* Alerts Section */}
      {alerts.length > 0 && (
        <div className="alerts-section">
          {alerts.slice(0, 3).map((alert) => (
            <AlertNotification
              key={alert.id}
              alert={alert}
              onAcknowledge={handleAcknowledgeAlert}
            />
          ))}
        </div>
      )}

      {/* Main Content: Split View */}
      <div className="dashboard-content">
        {/* Left Panel: Chat Messages */}
        <ChatPanel
          messages={messages}
          selectedMessage={selectedMessage}
          onSelectMessage={setSelectedMessage}
          onDeleteMessage={handleDeleteMessage}
        />

        {/* Right Panel: AI Risk Assessment */}
        <RiskAssessmentPanel
          selectedMessage={selectedMessage}
          onDeleteMessage={handleDeleteMessage}
        />
      </div>
    </div>
  );
};

export default Dashboard;
