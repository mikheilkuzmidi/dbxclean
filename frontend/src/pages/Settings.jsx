import React from 'react';

function Settings({ connection }) {
  const local = connection?.account_id === 'local';
  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
        <p className="text-secondary">Configuration and account information</p>
      </div>

      {/* Account Info */}
      <div className="card mb-4">
        <h3>{local ? 'Local Storage' : 'Dropbox Account'}</h3>
        <div style={{ marginTop: '1rem' }}>
          <div className="flex justify-between" style={{ padding: '0.5rem 0' }}>
            <span className="text-secondary">{local ? 'Root:' : 'Name:'}</span>
            <span>{connection?.name || 'Not connected'}</span>
          </div>
          {!local && <>
            <div className="flex justify-between" style={{ padding: '0.5rem 0' }}>
              <span className="text-secondary">Email:</span>
              <span>{connection?.email || 'Not available'}</span>
            </div>
            <div className="flex justify-between" style={{ padding: '0.5rem 0' }}>
              <span className="text-secondary">Account ID:</span>
              <span className="text-small">{connection?.account_id || 'Not available'}</span>
            </div>
          </>}
          <div className="flex justify-between" style={{ padding: '0.5rem 0' }}>
            <span className="text-secondary">Status:</span>
            <span className={`badge ${connection?.connected ? 'badge-success' : ''}`}>
              {connection?.connected ? 'Connected' : 'Not connected'}
            </span>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="card mb-4">
        <h3>Configuration</h3>
        <p className="text-secondary text-small mb-4">
          Edit <code>backend/.env</code> and restart the backend to change storage.
        </p>

        <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-sm)', fontFamily: 'monospace', fontSize: '0.875rem' }}>
          {local ? <>
            <div>STORAGE_MODE=local</div>
            <div>LOCAL_ROOT=/absolute/path/to/files</div>
          </> : <>
            <div>STORAGE_MODE=dropbox</div>
            <div>DROPBOX_ACCESS_TOKEN=your_token_here</div>
          </>}
        </div>
      </div>

      {/* How to Get Token */}
      {!local && <div className="card mb-4">
        <h3>How to Get Dropbox Access Token</h3>
        <ol style={{ marginLeft: '1.5rem', marginTop: '1rem' }}>
          <li style={{ marginBottom: '0.5rem' }}>
            Go to <a href="https://www.dropbox.com/developers/apps" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-blue)' }}>Dropbox App Console</a>
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Create a new app with "Full Dropbox" access
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Go to the "Permissions" tab and enable:
            <ul style={{ marginLeft: '1.5rem', marginTop: '0.25rem' }}>
              <li>files.metadata.read</li>
              <li>files.content.read</li>
              <li>files.content.write</li>
            </ul>
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Go to the "Settings" tab
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Generate an access token under "OAuth 2" section
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Copy the token to your <code>.env</code> file
          </li>
        </ol>
      </div>}

      {/* Analysis Settings */}
      <div className="card">
        <h3>Analysis Settings</h3>
        <p className="text-secondary text-small mb-4">
          Configure analysis parameters in <code>backend/.env</code>
        </p>

        <div style={{ display: 'grid', gap: '1rem' }}>
          <div>
            <strong>SIMILARITY_THRESHOLD</strong>
            <p className="text-small text-secondary">
              Lower values = more strict similarity matching (default: 5)
            </p>
          </div>
          <div>
            <strong>MAX_FILE_SIZE_MB</strong>
            <p className="text-small text-secondary">
              Maximum image file size to analyze (default: 100 MB)
            </p>
          </div>
          <div>
            <strong>PERCEPTUAL_HASH_SIZE</strong>
            <p className="text-small text-secondary">
              Hash size for image comparison (default: 8)
            </p>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="card" style={{ marginTop: '2rem', textAlign: 'center' }}>
        <h3>dbxclean</h3>
        <p className="text-secondary text-small">
          Review exact duplicates in Dropbox or local files
        </p>
      </div>
    </div>
  );
}

export default Settings;
