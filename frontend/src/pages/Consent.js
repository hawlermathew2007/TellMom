import { useState } from 'react';
import { useNavigate } from 'react-router-dom';  // ← ADD THIS
import axios from 'axios';
import './Consent.css';

const Consent = ({ onSubmit, parentData }) => {
  const navigate = useNavigate();  // ← ADD THIS
  const [formData, setFormData] = useState({
    child_name: '',
    child_roblox_username: '',
    child_roblox_id: '',
    data_retention_days: 30,
    consent_granted: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.consent_granted) {
      setError('You must agree to the terms to continue');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(
        'http://localhost:8000/api/auth/consent',
        formData
      );

      console.log('Consent response:', response.data);  // Debug log

      // Get child_id from response
      const childId = response.data.child_id;

      if (!childId) {
        setError('Failed to get child ID');
        setLoading(false);
        return;
      }

      // Call onSubmit to update parent state
      onSubmit(childId);

      // Show success message
      setTimeout(() => {
        // Navigate to dashboard
        navigate('/dashboard', { replace: true });
      }, 500);

    } catch (err) {
      console.error('Consent error:', err);  // Debug log
      const errorMessage =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Failed to submit consent';
      setError(errorMessage);
      setLoading(false);
    }
  };

  return (
    <div className="consent-container">
      <div className="consent-card">
        <h1>📋 Parental Consent</h1>

        <div className="privacy-notice">
          <h3>Privacy & Safety Notice</h3>
          <p>
            <strong>TellMom</strong> monitors your child's Roblox chat messages
            to detect potentially grooming behavior.
          </p>

          <h4>Data Collected:</h4>
          <ul>
            <li>Chat messages from Roblox</li>
            <li>Timestamps of messages</li>
            <li>Usernames of message senders</li>
          </ul>

          <h4>How We Use It:</h4>
          <ul>
            <li>AI analysis to detect grooming patterns</li>
            <li>Alert you of high-risk conversations</li>
            <li>Maintain audit logs for safety</li>
          </ul>

          <h4>Your Rights:</h4>
          <ul>
            <li>View all collected data anytime</li>
            <li>Delete any message</li>
            <li>Export your child's data</li>
            <li>Disable monitoring at any time</li>
          </ul>

          <h4>Data Retention:</h4>
          <p>
            Data will be automatically deleted after the retention period you
            specify (default: 30 days).
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="child_name">Child's Name</label>
            <input
              id="child_name"
              name="child_name"
              type="text"
              placeholder="e.g., Jane Doe"
              value={formData.child_name}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="child_roblox_username">Child's Roblox Username</label>
            <input
              id="child_roblox_username"
              name="child_roblox_username"
              type="text"
              placeholder="e.g., JaneDoe123"
              value={formData.child_roblox_username}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="child_roblox_id">Child's Roblox User ID</label>
            <input
              id="child_roblox_id"
              name="child_roblox_id"
              type="text"
              placeholder="e.g., 12345"
              value={formData.child_roblox_id}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="data_retention_days">
              Data Retention Period (days)
            </label>
            <input
              id="data_retention_days"
              name="data_retention_days"
              type="number"
              min="1"
              max="365"
              value={formData.data_retention_days}
              onChange={handleChange}
            />
            <small>Data will be automatically deleted after this period</small>
          </div>

          <div className="form-group checkbox">
            <input
              id="consent_granted"
              name="consent_granted"
              type="checkbox"
              checked={formData.consent_granted}
              onChange={handleChange}
            />
            <label htmlFor="consent_granted">
              I agree to the monitoring terms and understand how my child's data
              will be used
            </label>
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="btn-consent" disabled={loading}>
            {loading ? 'Setting up...' : 'I Agree & Continue'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Consent;
