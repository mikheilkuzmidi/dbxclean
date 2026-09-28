import React, { useState, useEffect } from 'react';
import { getSimilar, trashFiles, formatBytes, getImageUrl } from '../api';

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

    // SAFETY: Extra confirmation for large deletions
    if (pathsToDelete.length > 50) {
      const reallyConfirm = window.confirm(
        `Move ${pathsToDelete.length} images into recovery?\n\n` +
        `This is a large selection.\n\n` +
        `Click OK to proceed, or Cancel to go back.`
      );
      if (!reallyConfirm) {
        return;
      }
    }

    // SAFETY: Check for 100 file limit
    if (pathsToDelete.length > 100) {
      alert(`You can move up to 100 images at once. You selected ${pathsToDelete.length}.`);
      return;
    }

    try {
      setDeleting(true);
      const result = await trashFiles(pathsToDelete, true);

      if (result.failed_count > 0) {
        alert(
          `Recovery move completed:\n\n` +
          `Moved: ${result.trashed_count} images\n` +
          `❌ Failed: ${result.failed_count} images\n\n` +
          `Check the console for details about failed deletions.`
        );
        console.error('Failed moves:', result.failed);
      } else {
        alert(`Moved ${result.trashed_count} images into recovery.`);
      }

      if (result.trashed_count > 0) {
        loadSimilar(); // Reload data
      }

      setShowConfirm(false);
    } catch (error) {
      console.error('Failed to move images:', error);
      alert(`Error: ${error.response?.data?.detail || error.message}`);
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
            <h3>Selected Copy Bytes: {formatBytes(data.stats.space_can_save_bytes)}</h3>
            <p className="text-small text-secondary">
              {selectedCount} files selected ({formatBytes(selectedSize)})
            </p>
          </div>
          <button
            className="btn-danger"
            onClick={() => setShowConfirm(true)}
            disabled={selectedCount === 0 || deleting}
          >
            Move Selected to Recovery
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
                {file.path && (
                  <div className="file-thumbnail" style={{ marginRight: '1rem' }}>
                    <img
                      src={getImageUrl(file.path, true)}
                      alt={file.name}
                      style={{ width: 96, height: 96, objectFit: 'cover', borderRadius: '6px' }}
                    />
                  </div>
                )}
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
                    {typeof file.similarity_score === 'number' && (
                      <span className="ml-2 text-small" style={{ marginLeft: '0.5rem' }}>
                        Similarity: {Math.round(file.similarity_score * 100)}%
                      </span>
                    )}
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
              <h2>Confirm Recovery Move</h2>
            </div>
            <div>
              <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                Move {selectedCount} similar images into recovery?
              </p>
              <p className="text-secondary text-small mt-2">
                Selected images total {formatBytes(selectedSize)}.
              </p>
              <div style={{
                backgroundColor: 'var(--bg-tertiary)',
                padding: '1rem',
                borderRadius: 'var(--radius-sm)',
                marginTop: '1rem',
                border: '2px solid var(--accent-red)'
              }}>
                <p className="text-small" style={{ color: 'var(--accent-red)', fontWeight: 600 }}>
                  These images can be restored from the Recovery page.
                </p>
                <p className="text-small mt-2">
                  Dropbox recovery lasts for your account retention period. Local images remain in quarantine.
                </p>
                <p className="text-small mt-2" style={{ color: 'var(--accent-green)', fontWeight: 600 }}>
                  ✅ The best quality version of each image will be kept.
                </p>
                {selectedCount > 20 && (
                  <p className="text-small mt-2" style={{ color: 'var(--accent-yellow)', fontWeight: 600 }}>
                    ⚠️ Large deletion: {selectedCount} images
                  </p>
                )}
              </div>
              <p className="text-small text-secondary mt-2">
                Best quality images (highlighted) are protected.
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
                {deleting ? 'Moving...' : `Move ${selectedCount} Images`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Similar;
