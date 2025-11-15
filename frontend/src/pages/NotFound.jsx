import React from 'react';
import { Link } from 'react-router-dom';

function NotFound() {
  return (
    <div>
      <div className="page-header">
        <h1>Page Not Found</h1>
      </div>
      <div className="empty-state">
        <div className="empty-state-icon">🔍</div>
        <h3>404 - Page Not Found</h3>
        <p>The page you're looking for doesn't exist.</p>
        <Link to="/">
          <button className="btn-primary" style={{ marginTop: '1rem' }}>
            Go to Dashboard
          </button>
        </Link>
      </div>
    </div>
  );
}

export default NotFound;
