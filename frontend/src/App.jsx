import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation, Link } from 'react-router-dom';
import './App.css';
import { checkConnection } from './api';
import Dashboard from './pages/Dashboard';
import Duplicates from './pages/Duplicates';
import Similar from './pages/Similar';
import Files from './pages/Files';
import Settings from './pages/Settings';
import NotFound from './pages/NotFound';

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
            <NavLink to="/" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"} end>
              <span className="nav-icon">📊</span>
              Dashboard
            </NavLink>
            <NavLink to="/duplicates" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
              <span className="nav-icon">📋</span>
              Duplicates
            </NavLink>
            <NavLink to="/similar" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
              <span className="nav-icon">🖼️</span>
              Similar Images
            </NavLink>
            <NavLink to="/files" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
              <span className="nav-icon">📁</span>
              All Files
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
              <span className="nav-icon">⚙️</span>
              Settings
            </NavLink>
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
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
