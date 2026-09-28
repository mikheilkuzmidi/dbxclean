import React, { useEffect, useState } from 'react';
import { getRecovery, restoreFiles, formatBytes } from '../api';

function Recovery() {
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const load = async () => {
    try {
      const result = await getRecovery();
      setFiles(result.files);
      setError('');
    } catch (failure) {
      setError(failure.response?.data?.detail || failure.message);
    }
  };

  useEffect(() => { load(); }, []);

  const restore = async () => {
    const ids = files.filter(file => selected[file.id]).map(file => file.id);
    if (!ids.length) return;
    setShowConfirm(false);
    setBusy(true);
    try {
      const result = await restoreFiles(ids, true);
      if (result.failed_count) {
        setError(result.failed.map(item => `${item.path}: ${item.error}`).join('\n'));
      } else {
        setError('');
      }
      setSelected({});
      await load();
    } catch (failure) {
      setError(failure.response?.data?.detail || failure.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Recovery</h1>
        <p className="text-secondary">Restore reviewed files to their original paths.</p>
      </div>
      {error && <p role="alert" style={{ color: 'var(--accent-red)', whiteSpace: 'pre-wrap' }}>{error}</p>}
      <div className="card mb-4">
        <p className="text-small text-secondary">
          Local files stay in quarantine. Dropbox files stay in Deleted files for your account retention period.
        </p>
        <button className="btn-primary" onClick={() => setShowConfirm(true)} disabled={busy || !Object.values(selected).some(Boolean)}>
          {busy ? 'Restoring...' : 'Restore Selected'}
        </button>
      </div>
      <div className="file-list">
        {files.length === 0 && <div className="empty-state">No files in recovery</div>}
        {files.map(file => (
          <label className="file-item" key={file.id}>
            <input
              type="checkbox"
              checked={Boolean(selected[file.id])}
              onChange={() => setSelected(previous => ({ ...previous, [file.id]: !previous[file.id] }))}
            />
            <div className="file-info">
              <div className="file-name">{file.path}</div>
              <div className="file-meta">{formatBytes(file.size)} • {file.backend}</div>
            </div>
          </label>
        ))}
      </div>
      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="modal" onClick={event => event.stopPropagation()}>
            <div className="modal-header"><h2>Confirm Restore</h2></div>
            <p>Restore {Object.values(selected).filter(Boolean).length} files to their original paths?</p>
            <p className="text-secondary text-small mt-2">Restoration stops if the original path is occupied.</p>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowConfirm(false)}>Cancel</button>
              <button className="btn-primary" onClick={restore} disabled={busy}>Restore Files</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Recovery;
