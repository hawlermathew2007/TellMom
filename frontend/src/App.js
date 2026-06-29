import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Consent from './pages/Consent';

function App() {
  const [parentData, setParentData] = useState(null);
  const [childId, setChildId] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check if parent already logged in
    const token = localStorage.getItem('token');
    const savedParent = localStorage.getItem('parentData');
    const savedChildId = localStorage.getItem('childId');

    if (token && savedParent) {
      setParentData(JSON.parse(savedParent));
      setIsAuthenticated(true);
      
      if (savedChildId) {
        setChildId(savedChildId);
      }
    }
  }, []);

  const handleLogin = (token, parent) => {
    localStorage.setItem('token', token);
    localStorage.setItem('parentData', JSON.stringify(parent));
    setParentData(parent);
    setIsAuthenticated(true);
  };

  const handleSignup = (token, parent) => {
    localStorage.setItem('token', token);
    localStorage.setItem('parentData', JSON.stringify(parent));
    setParentData(parent);
    setIsAuthenticated(true);
  };

  const handleConsentSubmit = (childId) => {
    console.log('Setting childId:', childId);  // Debug log
    localStorage.setItem('childId', childId);
    setChildId(childId);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('parentData');
    localStorage.removeItem('childId');
    setParentData(null);
    setChildId(null);
    setIsAuthenticated(false);
  };

  return (
    <Routes>
      {/* Public Routes */}
      <Route 
        path="/login" 
        element={
          isAuthenticated ? 
            <Navigate to={childId ? "/dashboard" : "/consent"} /> : 
            <Login onLogin={handleLogin} />
        } 
      />
      
      <Route 
        path="/signup" 
        element={
          isAuthenticated ? 
            <Navigate to="/consent" /> : 
            <Signup onSignup={handleSignup} />
        } 
      />

      {/* Protected Routes */}
      <Route 
        path="/consent" 
        element={
          isAuthenticated ? 
            <Consent onSubmit={handleConsentSubmit} parentData={parentData} /> : 
            <Navigate to="/login" />
        } 
      />
      
      <Route 
        path="/dashboard" 
        element={
          isAuthenticated && childId ? 
            <Dashboard childId={childId} onLogout={handleLogout} /> : 
            <Navigate to="/login" />
        } 
      />

      {/* Default Route */}
      <Route 
        path="/" 
        element={
          isAuthenticated ? 
            (childId ? <Navigate to="/dashboard" /> : <Navigate to="/consent" />) : 
            <Navigate to="/login" />
        } 
      />
    </Routes>
  );
}

export default App;
