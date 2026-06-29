import React from 'react';
import './AlertNotification.css';

const AlertNotification = ({ alert, onAcknowledge }) => {
  const riskColor = {
    RED: '#ff6b6b',
    YELLOW: '#ffd93d',
    GREEN: '#51cf66',
  }[alert.risk_level];

  const riskIcon = {
    RED: '🚨',
    YELLOW: '⚠️',
    GREEN: '✅',
  }[alert.risk_level];

  return (
    <div className="alert-notification" style={{ borderLeftColor: riskColor }}>
      <div className="alert-header">
        <span className="alert-icon">{riskIcon}</span>
        <span className="alert-title">
          {alert.risk_level === 'RED'
            ? 'High Risk Message Detected'
            : 'Suspicious Activity Detected'}
        </span>
        {!alert.acknowledged && <span className="alert-badge">NEW</span>}
      </div>

      <div className="alert-content">
        <p className="alert-message">"{alert.message_preview}"</p>
        <div className="alert-meta">
          <span className="risk-score">Risk: {(alert.risk_score * 100).toFixed(0)}%</span>
          <span className="time">{new Date(alert.triggered_at).toLocaleTimeString()}</span>
        </div>
      </div>

      {!alert.acknowledged && (
        <button
          className="btn-acknowledge"
          onClick={() => onAcknowledge(alert.id)}
        >
          Acknowledge
        </button>
      )}
    </div>
  );
};

export default AlertNotification;
