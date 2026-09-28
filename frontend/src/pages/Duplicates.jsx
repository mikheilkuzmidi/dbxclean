import React, { useState, useEffect } from 'react';
import { getDuplicates, trashFiles, formatBytes, getImageUrl } from '../api';

function Duplicates() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedFiles, setSelectedFiles] = useState({});
  const [showConfirm, setShowConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    loadDuplicates();
  }, []);

  const loadDuplicates = async (nextOffset = 0) => {
    try {
      const result = await getDuplicates(100, nextOffset);
      setData(previous => nextOffset ? { ...result, groups: [...(previous?.groups || []), ...result.groups] } : result);
      setOffset(nextOffset);

      // Pre-select files to delete (all except recommended)
      const selected = {};
      result.groups?.forEach(group => {
        group.files.forEach(file => {
          if (!file.is_recommended) {
            selected[file.path] = true;
          }
        });
      });
      setSelectedFiles(previous => nextOffset ? { ...previous, ...selected } : selected);
    } catch (error) {
      console.error('Failed to load duplicates:', error);
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

    // Ask for confirmation on a large recovery move.
    if (pathsToDelete.length > 50) {
      const reallyConfirm = window.confirm(
        `Move ${pathsToDelete.length} files into recovery?\n\n` +
        `This is a large selection.\n\n` +
        `Click OK to proceed, or Cancel to go back.`
      );
      if (!reallyConfirm) {
        return;
      }
    }

    // SAFETY: Check for 100 file limit
    if (pathsToDelete.length > 100) {
      alert(`You can move up to 100 files at once. You selected ${pathsToDelete.length}.`);
      return;
    }

    try {
      setDeleting(true);
      const result = await trashFiles(pathsToDelete, true);

      if (result.failed_count > 0) {
        alert(
          `Recovery move completed:\n\n` +
          `Moved: ${result.trashed_count} files\n` +
          `❌ Failed: ${result.failed_count} files\n\n` +
          `Check the console for details about failed deletions.`
        );
        console.error('Failed moves:', result.failed);
      } else {
        alert(`Moved ${result.trashed_count} files into recovery.`);
      }

      if (result.trashed_count > 0) {
        loadDuplicates();
      }

      setShowConfirm(false);
    } catch (error) {
      console.error('Failed to move files:', error);
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setDeleting(false);
    }
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
          <h1>Duplicate Files</h1>
        </div>
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <h3>No Duplicates Found</h3>
          <p>Run a scan to find duplicate files</p>
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
        <h1>Duplicate Files</h1>
        <p className="text-secondary">
          Found {data.stats.duplicate_groups} groups with {data.stats.total_duplicate_files} duplicate files
        </p>
      </div>

      {/* Summary Card */}
      <div className="card mb-4">
        <div className="flex justify-between items-center">
          <div>
            <h3>Space Wasted: {formatBytes(data.stats.space_wasted_bytes)}</h3>
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

      {/* Duplicate Groups */}
      {data.groups.map((group, idx) => (
        <div key={idx} className="group-card">
          <div className="group-header">
            <div>
              <h4>{group.file_count} identical files</h4>
              <p className="text-small text-secondary">
                {formatBytes(group.total_size)} total • {formatBytes(group.space_can_save)} in extra copies
              </p>
            </div>
          </div>

          <div className="group-files">
            {group.files.map((file) => (
              <div
                key={file.path}
                className={`group-file-item ${file.is_recommended ? 'recommended' : ''}`}
              >
                {file.is_image && file.path && (
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
                  disabled={file.is_recommended}
                  style={{ marginRight: '1rem' }}
                />
                <div style={{ flex: 1 }}>
                  <div className="file-name">{file.name}</div>
                  <div className="file-meta">
                    {file.path} • {formatBytes(file.size)}
                    {file.is_recommended && (
                      <span className="badge badge-success" style={{ marginLeft: '0.5rem' }}>
                        Recommended Keep
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
      {data.has_more && (
        <button className="btn-secondary" onClick={() => loadDuplicates(offset + 100)}>
          Load More Groups
        </button>
      )}

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Confirm Recovery Move</h2>
            </div>
            <div>
              <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                Move {selectedCount} files into recovery?
              </p>
              <p className="text-secondary text-small mt-2">
                Selected files total {formatBytes(selectedSize)}.
              </p>
              <div style={{
                backgroundColor: 'var(--bg-tertiary)',
                padding: '1rem',
                borderRadius: 'var(--radius-sm)',
                marginTop: '1rem',
                border: '2px solid var(--accent-red)'
              }}>
                <p className="text-small" style={{ color: 'var(--accent-red)', fontWeight: 600 }}>
                  These files can be restored from the Recovery page.
                </p>
                <p className="text-small mt-2">
                  Dropbox recovery lasts for your account retention period. Local files remain in quarantine.
                </p>
                {selectedCount > 20 && (
                  <p className="text-small mt-2" style={{ color: 'var(--accent-yellow)', fontWeight: 600 }}>
                    ⚠️ Large deletion: {selectedCount} files
                  </p>
                )}
              </div>
              <p className="text-small text-secondary mt-2">
                Recommended files (highlighted in green) are protected.
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
                {deleting ? 'Moving...' : `Move ${selectedCount} Files`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Duplicates;
