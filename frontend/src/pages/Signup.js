import { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';
import './Signup.css';

const Signup = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    full_name: '',
    phone_number: '',
    password: '',
    password_confirm: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [passwordStrength, setPasswordStrength] = useState(0);

  // Handle input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });

    // Check password strength
    if (name === 'password') {
      checkPasswordStrength(value);
    }
  };

  // Check password strength
  const checkPasswordStrength = (password) => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[!@#$%^&*]/.test(password)) strength++;
    setPasswordStrength(strength);
  };

  // Validate form
  const validateForm = () => {
    if (!formData.email || !formData.full_name || !formData.password) {
      setError('Please fill in all required fields');
      return false;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Please enter a valid email address');
      return false;
    }

    // Password length
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return false;
    }

    // Passwords match
    if (formData.password !== formData.password_confirm) {
      setError('Passwords do not match');
      return false;
    }

    return true;
  };

  // Handle signup
  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(
        'http://localhost:8000/api/auth/register-parent',
        {
          email: formData.email,
          full_name: formData.full_name,
          phone_number: formData.phone_number || null,
          password: formData.password,
          password_confirm: formData.password_confirm,
        }
      );

      // Store token and redirect
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('parentData', JSON.stringify(response.data.parent));

      setSuccess('✅ Account created successfully! Redirecting...');

      // Redirect to consent page after 2 seconds
      setTimeout(() => {
        navigate('/consent', {
          state: { parentData: response.data.parent, isNewSignup: true },
        });
      }, 2000);
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Signup failed. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Get password strength color and text
  const getPasswordStrengthInfo = () => {
    const strengths = [
      { text: 'Very Weak', color: '#d32f2f', width: '20%' },
      { text: 'Weak', color: '#f57c00', width: '40%' },
      { text: 'Fair', color: '#fbc02d', width: '60%' },
      { text: 'Good', color: '#7cb342', width: '80%' },
      { text: 'Strong', color: '#388e3c', width: '100%' },
    ];
    return strengths[passwordStrength] || strengths[0];
  };

  const strengthInfo = getPasswordStrengthInfo();

  return (
    <div className="signup-container">
      <div className="signup-card">
        <h1>🛡️ TellMom</h1>
        <p className="subtitle">Create your parent account</p>

        <form onSubmit={handleSignup}>
          {/* Full Name */}
          <div className="form-group">
            <label htmlFor="full_name">Full Name *</label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              placeholder="John Doe"
              value={formData.full_name}
              onChange={handleChange}
              required
            />
          </div>

          {/* Email */}
          <div className="form-group">
            <label htmlFor="email">Email Address *</label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="your@email.com"
              value={formData.email}
              onChange={handleChange}
              required
            />
            <small className="hint">We'll verify this email before monitoring starts</small>
          </div>

          {/* Phone Number */}
          <div className="form-group">
            <label htmlFor="phone_number">Phone Number (Optional)</label>
            <input
              id="phone_number"
              name="phone_number"
              type="tel"
              placeholder="+1 (555) 123-4567"
              value={formData.phone_number}
              onChange={handleChange}
            />
            <small className="hint">For urgent notifications</small>
          </div>

          {/* Password */}
          <div className="form-group">
            <label htmlFor="password">Password *</label>
            <input
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
              required
            />
            <small className="hint">
              At least 8 characters with uppercase, lowercase, and numbers
            </small>

            {/* Password Strength Indicator */}
            {formData.password && (
              <div className="password-strength">
                <div className="strength-bar">
                  <div
                    className="strength-fill"
                    style={{
                      width: strengthInfo.width,
                      backgroundColor: strengthInfo.color,
                    }}
                  ></div>
                </div>
                <span className="strength-text" style={{ color: strengthInfo.color }}>
                  Strength: {strengthInfo.text}
                </span>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div className="form-group">
            <label htmlFor="password_confirm">Confirm Password *</label>
            <input
              id="password_confirm"
              name="password_confirm"
              type="password"
              placeholder="••••••••"
              value={formData.password_confirm}
              onChange={handleChange}
              required
            />
            {formData.password && formData.password_confirm && (
              <small className="hint">
                {formData.password === formData.password_confirm ? (
                  <span style={{ color: '#388e3c' }}>✅ Passwords match</span>
                ) : (
                  <span style={{ color: '#d32f2f' }}>❌ Passwords do not match</span>
                )}
              </small>
            )}
          </div>

          {/* Error Message */}
          {error && <div className="error-message">{error}</div>}

          {/* Success Message */}
          {success && <div className="success-message">{success}</div>}

          {/* Terms */}
          <div className="terms">
            <p>
              By signing up, you agree to our{' '}
              <a href="#privacy" target="_blank" rel="noopener noreferrer">
                Privacy Policy
              </a>{' '}
              and{' '}
              <a href="#terms" target="_blank" rel="noopener noreferrer">
                Terms of Service
              </a>
              . We comply with COPPA regulations for child safety.
            </p>
          </div>

          {/* Signup Button */}
          <button type="submit" className="btn-signup" disabled={loading}>
            {loading ? '⏳ Creating Account...' : '✨ Create Account'}
          </button>
        </form>

        {/* Login Link */}
        <p className="login-link">
          Already have an account?{' '}
          <Link to="/login">
            <strong>Login</strong>
          </Link>
        </p>
      </div>

      {/* Info Section */}
      <div className="signup-info">
        <div className="info-card">
          <h3>🔒 Why Sign Up?</h3>
          <ul>
            <li>Monitor your child's Roblox chat in real-time</li>
            <li>AI-powered grooming detection</li>
            <li>Instant alerts for suspicious messages</li>
            <li>COPPA-compliant privacy controls</li>
          </ul>
        </div>

        <div className="info-card">
          <h3>📋 What We Collect</h3>
          <ul>
            <li>Chat messages from Roblox</li>
            <li>Message timestamps</li>
            <li>Sender information</li>
            <li>AI analysis results</li>
          </ul>
        </div>

        <div className="info-card">
          <h3>✅ Your Control</h3>
          <ul>
            <li>You decide data retention period</li>
            <li>Delete messages anytime</li>
            <li>Export your child's data</li>
            <li>Disable monitoring instantly</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Signup;
