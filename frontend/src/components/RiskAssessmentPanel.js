import React from 'react';
import './RiskAssessmentPanel.css';

const RiskAssessmentPanel = ({ selectedMessage, onDeleteMessage }) => {
  if (!selectedMessage) {
    return (
      <div className="risk-panel">
        <div className="no-selection">
          <p>👈 Select a message to view AI analysis</p>
        </div>
      </div>
    );
  }

  const analysis = selectedMessage.analysis;

  const getRiskColor = (level) => {
    if (level === 'RED') return '#ff6b6b';
    if (level === 'YELLOW') return '#ffd93d';
    return '#51cf66';
  };

  const getRiskIcon = (level) => {
    if (level === 'RED') return '🚨';
    if (level === 'YELLOW') return '⚠️';
    return '✅';
  };

  return (
    <div className="risk-panel">
      {analysis ? (
        <div className="analysis-container">
          <div className="analysis-header">
            <h2>🤖 AI Analysis</h2>
          </div>

          {/* Risk Score Card */}
          <div className="risk-card">
            <div className="risk-circle-container">
              <div
                className="risk-circle"
                style={{
                  background: `conic-gradient(${getRiskColor(analysis.risk_level)} 0deg ${
                    analysis.risk_score * 360
                  }deg, #e0e0e0 ${analysis.risk_score * 360}deg)`,
                }}
              >
                <div className="risk-circle-inner">
                  <div className="risk-percentage">
                    {(analysis.risk_score * 100).toFixed(0)}%
                  </div>
                  <div className="risk-label">{analysis.risk_level}</div>
                </div>
              </div>
            </div>

            <div className="risk-details">
              <div className="detail-row">
                <span className="label">Risk Level:</span>
                <span
                  className="value"
                  style={{ color: getRiskColor(analysis.risk_level), fontWeight: 'bold' }}
                >
                  {getRiskIcon(analysis.risk_level)} {analysis.risk_level}
                </span>
              </div>
              <div className="detail-row">
                <span className="label">Confidence:</span>
                <span className="value">{(analysis.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="detail-row">
                <span className="label">Analyzed At:</span>
                <span className="value">{new Date(analysis.analyzed_at).toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Explanation */}
          <div className="explanation-card">
            <h3>📝 Analysis Explanation</h3>
            <p>{analysis.explanation}</p>
          </div>

          {/* Flagged Phrases */}
          {analysis.flagged_phrases.length > 0 && (
            <div className="flagged-phrases-card">
              <h3>🚩 Flagged Phrases</h3>
              <div className="phrases-list">
                {analysis.flagged_phrases.map((phrase, idx) => (
                  <span key={idx} className="phrase-tag">
                    "{phrase}"
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Original Message */}
          <div className="original-message-card">
            <h3>💬 Original Message</h3>
            <div className="message-content">
              <p className="sender">From: {selectedMessage.username}</p>
              <p className="text">{selectedMessage.text}</p>
              <p className="timestamp">
                {new Date(selectedMessage.timestamp).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="actions">
            <button
              className="btn-delete"
              onClick={() => {
                if (window.confirm('Delete this message?')) {
                  onDeleteMessage(selectedMessage.id);
                }
              }}
            >
              🗑️ Delete Message
            </button>
            <button className="btn-report">📧 Report to Roblox</button>
          </div>
        </div>
      ) : (
        <div className="no-analysis">
          <p>No analysis available for this message</p>
        </div>
      )}
    </div>
  );
};

export default RiskAssessmentPanel;
