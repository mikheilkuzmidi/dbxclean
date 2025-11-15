import React, { useState, useEffect } from 'react';
import { getSimilar, deleteFiles, formatBytes } from '../api';

function Similar() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedFiles, setSelectedFiles] = useState({});
  const [showConfirm, setShowConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadSimilar();
  }, []);

  const loadSimilar = async () => {
    try {
      const result = await getSimilar();
      setData(result);

      // Pre-select files to delete (all except best quality)
      const selected = {};
      result.groups?.forEach(group => {
        group.files.forEach(file => {
          if (!file.is_best_quality) {
            selected[file.path] = true;
          }
        });
      });
      setSelectedFiles(selected);
    } catch (error) {
      console.error('Failed to load similar images:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleFileSelection = (path) => {
    setSelectedFiles(prev => ({
      ...prev,
      [path]: !prev[path]
    }));
  };

  const handleDeleteSelected = async () => {
    const pathsToDelete = Object.keys(selectedFiles).filter(path => selectedFiles[path]);

    if (pathsToDelete.length === 0) {
      alert('No files selected');
      return;
    }

    try {
      setDeleting(true);
      const result = await deleteFiles(pathsToDelete, true);

      alert(`Deleted ${result.deleted_count} files. Failed: ${result.failed_count}`);

      if (result.deleted_count > 0) {
        loadSimilar(); // Reload data
      }

      setShowConfirm(false);
    } catch (error) {
      console.error('Failed to delete files:', error);
      alert('Failed to delete files: ' + error.message);
    } finally {
      setDeleting(false);
    }
  };

  const getQualityColor = (score) => {
    if (score >= 80) return 'var(--accent-green)';
    if (score >= 60) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '400px' }}>
        <div className="spinner"></div>
      </div>
    );
  }

  if (!data?.groups || data.groups.length === 0) {
    return (
      <div>
        <div className="page-header">
          <h1>Similar Images</h1>
        </div>
        <div className="empty-state">
          <div className="empty-state-icon">🖼️</div>
          <h3>No Similar Images Found</h3>
          <p>Run a scan with image analysis to find similar images</p>
        </div>
      </div>
    );
  }

  const selectedCount = Object.values(selectedFiles).filter(Boolean).length;
  const selectedSize = data.groups.reduce((total, group) => {
    return total + group.files.reduce((sum, file) => {
      return sum + (selectedFiles[file.path] ? file.size : 0);
    }, 0);
  }, 0);

  return (
    <div>
      <div className="page-header">
        <h1>Similar Images</h1>
        <p className="text-secondary">
          Found {data.stats.similar_groups} groups with {data.stats.total_similar_files} similar images
        </p>
      </div>

      {/* Summary Card */}
      <div className="card mb-4">
        <div className="flex justify-between items-center">
          <div>
            <h3>Space Can Save: {formatBytes(data.stats.space_can_save_bytes)}</h3>
            <p className="text-small text-secondary">
              {selectedCount} files selected ({formatBytes(selectedSize)})
            </p>
          </div>
          <button
            className="btn-danger"
            onClick={() => setShowConfirm(true)}
            disabled={selectedCount === 0 || deleting}
          >
            Delete Selected
          </button>
        </div>
      </div>

      {/* Similar Groups */}
      {data.groups.map((group, idx) => (
        <div key={idx} className="group-card">
          <div className="group-header">
            <div>
              <h4>{group.file_count} similar images</h4>
              <p className="text-small text-secondary">
                Images look similar but may have different resolutions or quality
              </p>
            </div>
          </div>

          <div className="group-files">
            {group.files.map((file) => (
              <div
                key={file.path}
                className={`group-file-item ${file.is_best_quality ? 'recommended' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={selectedFiles[file.path] || false}
                  onChange={() => toggleFileSelection(file.path)}
                  disabled={file.is_best_quality}
                  style={{ marginRight: '1rem' }}
                />
                <div style={{ flex: 1 }}>
                  <div className="file-name">{file.name}</div>
                  <div className="file-meta">
                    {file.path} • {file.width}×{file.height} • {formatBytes(file.size)}
                    {file.quality_score && (
                      <span
                        style={{
                          marginLeft: '0.5rem',
                          color: getQualityColor(file.quality_score),
                          fontWeight: 600
                        }}
                      >
                        Quality: {Math.round(file.quality_score)}%
                      </span>
                    )}
                    {file.is_best_quality && (
                      <span className="badge badge-success" style={{ marginLeft: '0.5rem' }}>
                        Best Quality
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Confirm Deletion</h2>
            </div>
            <div>
              <p>Are you sure you want to delete {selectedCount} similar images?</p>
              <p className="text-secondary text-small mt-2">
                This will free up {formatBytes(selectedSize)} of space.
              </p>
              <p className="text-small mt-2">
                The best quality version of each image will be kept.
              </p>
              <p className="text-small mt-2" style={{ color: 'var(--accent-red)' }}>
                ⚠️ This action cannot be undone!
              </p>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => setShowConfirm(false)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="btn-danger"
                onClick={handleDeleteSelected}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete Files'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Similar;
