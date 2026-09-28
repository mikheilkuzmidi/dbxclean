import React, { useState, useEffect } from 'react';
import { getStats, startScan, getJobStatus, formatBytes } from '../api';

function Dashboard({ connection }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(null);
  const [scanPath, setScanPath] = useState('');
  const [analyzeImages, setAnalyzeImages] = useState(false);
  const [scanError, setScanError] = useState(null);
  const pollRef = React.useRef(null);

  useEffect(() => {
    loadStats();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const loadStats = async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartScan = async () => {
    try {
      setScanning(true);
      setScanError(null);
      const job = await startScan(scanPath, true, analyzeImages);
      setScanProgress({ ...job, progress: 0 });

      // Poll for job status
      pollRef.current = setInterval(async () => {
        try {
          const status = await getJobStatus(job.job_id);
          setScanProgress(status);
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setScanning(false);
            if (status.status === 'failed') {
              setScanError(status.error_message);
            } else {
              loadStats();
            }
          }
        } catch (error) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setScanning(false);
          setScanError(error.message);
        }
      }, 2000);
    } catch (error) {
      console.error('Failed to start scan:', error);
      setScanning(false);
      setScanError(error.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '400px' }}>
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p className="text-secondary">Overview of {connection?.account_id === 'local' ? 'your local files' : 'your Dropbox files'}</p>
      </div>

      {/* Scan Controls */}
      <div className="card mb-4">
        <h3>Start Analysis</h3>
        <p className="text-secondary text-small mb-4">
          Scan {connection?.account_id === 'local' ? 'your local directory' : 'Dropbox'} to find duplicates and similar images
        </p>

        <div className="flex gap-4 items-center">
          <input
            type="text"
            placeholder="Path to scan (leave empty for root)"
            value={scanPath}
            onChange={(e) => setScanPath(e.target.value)}
            disabled={scanning}
            style={{ flex: 1 }}
          />
          <button
            className="btn-primary"
            onClick={handleStartScan}
            disabled={scanning}
          >
            {scanning ? 'Scanning...' : 'Start Scan'}
          </button>
        </div>
        <label className="flex gap-2 items-center mt-2 text-small">
          <input
            type="checkbox"
            checked={analyzeImages}
            onChange={(event) => setAnalyzeImages(event.target.checked)}
            disabled={scanning}
          />
          Also find similar images (downloads image data for analysis)
        </label>

        {scanError && (
          <p className="text-small text-secondary mt-2" style={{ color: 'var(--accent-red)' }}>
            Error: {scanError}
          </p>
        )}

        {scanProgress && (
          <div className="mt-2">
            <div className="flex justify-between text-small mb-2">
              <span>{scanProgress.status}</span>
              <span>{scanProgress.status === 'completed' ? '100%' : scanProgress.status === 'failed' ? 'Failed' : 'Scanning'}</span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${scanProgress.progress}%` }}
              ></div>
            </div>
            {scanProgress.processed_files > 0 && (
              <p className="text-small text-secondary mt-2">
                Processed {scanProgress.processed_files.toLocaleString()} files
              </p>
            )}
          </div>
        )}
      </div>

      {/* Statistics */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Files</div>
          <div className="stat-value">{stats?.total_files?.toLocaleString() || 0}</div>
          <div className="text-small text-secondary">
            {stats?.total_images?.toLocaleString() || 0} images
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Duplicate Groups</div>
          <div className="stat-value">
            {stats?.duplicates?.duplicate_groups?.toLocaleString() || 0}
          </div>
          <div className="text-small text-secondary">
            {stats?.duplicates?.total_duplicate_files?.toLocaleString() || 0} duplicate files
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Similar Image Groups</div>
          <div className="stat-value">
            {stats?.similar?.similar_groups?.toLocaleString() || 0}
          </div>
          <div className="text-small text-secondary">
            {stats?.similar?.total_similar_files?.toLocaleString() || 0} similar images
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Duplicate Data</div>
          <div className="stat-value" style={{ color: 'var(--accent-green)' }}>
            {formatBytes(
              (stats?.duplicates?.space_wasted_bytes || 0) +
              (stats?.similar?.space_can_save_bytes || 0)
            )}
          </div>
          <div className="text-small text-secondary">
            Extra copy bytes and reviewed similar images
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h3>Quick Actions</h3>
        <div className="flex gap-4 mt-2" style={{ flexWrap: 'wrap' }}>
          <button className="btn-secondary" onClick={() => window.location.href = '/duplicates'}>
            View Duplicates
          </button>
          <button className="btn-secondary" onClick={() => window.location.href = '/similar'}>
            View Similar Images
          </button>
          <button className="btn-secondary" onClick={() => window.location.href = '/files'}>
            Browse All Files
          </button>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
