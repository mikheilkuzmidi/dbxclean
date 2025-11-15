import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import { checkConnection } from './api';
import Dashboard from './pages/Dashboard';
import Duplicates from './pages/Duplicates';
import Similar from './pages/Similar';
import Files from './pages/Files';
import Settings from './pages/Settings';

function App() {
  const [connection, setConnection] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConnection();
  }, []);

  const loadConnection = async () => {
    try {
      const data = await checkConnection();
      setConnection(data);
    } catch (error) {
      console.error('Failed to check connection:', error);
      setConnection({ connected: false, error: 'Failed to connect' });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Connecting to Dropbox...</p>
      </div>
    );
  }

  if (!connection?.connected) {
    return (
      <div className="error-screen">
        <h1>Connection Error</h1>
        <p>Unable to connect to Dropbox. Please configure your access token.</p>
        {connection?.error && <p className="text-secondary">{connection.error}</p>}
        <Link to="/settings">
          <button className="btn-primary">Go to Settings</button>
        </Link>
      </div>
    );
  }

  return (
    <Router>
      <div className="app">
        <nav className="sidebar">
          <div className="sidebar-header">
            <h2>Dropbox Sorter</h2>
            <p className="text-small text-secondary">{connection.name}</p>
          </div>

          <div className="sidebar-nav">
            <Link to="/" className="nav-item">
              <span className="nav-icon">📊</span>
              Dashboard
            </Link>
            <Link to="/duplicates" className="nav-item">
              <span className="nav-icon">📋</span>
              Duplicates
            </Link>
            <Link to="/similar" className="nav-item">
              <span className="nav-icon">🖼️</span>
              Similar Images
            </Link>
            <Link to="/files" className="nav-item">
              <span className="nav-icon">📁</span>
              All Files
            </Link>
            <Link to="/settings" className="nav-item">
              <span className="nav-icon">⚙️</span>
              Settings
            </Link>
          </div>

          <div className="sidebar-footer">
            <p className="text-tiny text-secondary">
              v1.0.0
            </p>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/duplicates" element={<Duplicates />} />
            <Route path="/similar" element={<Similar />} />
            <Route path="/files" element={<Files />} />
            <Route path="/settings" element={<Settings connection={connection} />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
