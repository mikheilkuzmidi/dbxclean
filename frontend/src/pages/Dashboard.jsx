import React, { useState, useEffect } from 'react';
import { getStats, startScan, getJobStatus, formatBytes } from '../api';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(null);
  const [scanPath, setScanPath] = useState('');

  useEffect(() => {
    loadStats();
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
      const job = await startScan(scanPath, true, true);
      setScanProgress({ ...job, progress: 0 });

      // Poll for job status
      const interval = setInterval(async () => {
        const status = await getJobStatus(job.job_id);
        setScanProgress(status);

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
          setScanning(false);
          loadStats(); // Reload stats after scan completes
        }
      }, 2000);
    } catch (error) {
      console.error('Failed to start scan:', error);
      setScanning(false);
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
        <p className="text-secondary">Overview of your Dropbox organization</p>
      </div>

      {/* Scan Controls */}
      <div className="card mb-4">
        <h3>Start Analysis</h3>
        <p className="text-secondary text-small mb-4">
          Scan your Dropbox to find duplicates and similar images
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

        {scanProgress && (
          <div className="mt-2">
            <div className="flex justify-between text-small mb-2">
              <span>{scanProgress.status}</span>
              <span>{Math.round(scanProgress.progress)}%</span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${scanProgress.progress}%` }}
              ></div>
            </div>
            {scanProgress.processed_files > 0 && (
              <p className="text-small text-secondary mt-2">
                Processed {scanProgress.processed_files} / {scanProgress.total_files} files
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
          <div className="stat-label">Space Can Save</div>
          <div className="stat-value" style={{ color: 'var(--accent-green)' }}>
            {formatBytes(
              (stats?.duplicates?.space_wasted_bytes || 0) +
              (stats?.similar?.space_can_save_bytes || 0)
            )}
          </div>
          <div className="text-small text-secondary">
            By removing duplicates and similar images
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
