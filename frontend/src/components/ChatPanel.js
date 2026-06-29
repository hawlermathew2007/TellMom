import React from 'react';
import './ChatPanel.css';

const ChatPanel = ({ messages, selectedMessage, onSelectMessage, onDeleteMessage }) => {
  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>💬 Chat Messages</h2>
        <span className="message-count">{messages.length}</span>
      </div>

      <div className="messages-list">
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>No messages yet. Waiting for activity...</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`message-item ${selectedMessage?.id === message.id ? 'selected' : ''} ${
                message.analysis?.risk_level === 'RED'
                  ? 'risk-red'
                  : message.analysis?.risk_level === 'YELLOW'
                  ? 'risk-yellow'
                  : 'risk-green'
              }`}
              onClick={() => onSelectMessage(message)}
            >
              <div className="message-header">
                <span className="username">👤 {message.username}</span>
                <span className="time">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="message-text">{message.text}</p>
              {message.analysis && (
                <div className="message-risk-badge">
                  <span className={`badge badge-${message.analysis.risk_level.toLowerCase()}`}>
                    {message.analysis.risk_level}
                  </span>
                  <span className="risk-score">
                    {(message.analysis.risk_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ChatPanel;
