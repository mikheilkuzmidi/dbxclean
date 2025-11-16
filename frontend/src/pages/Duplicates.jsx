import React, { useState, useEffect } from 'react';
import { getDuplicates, deleteFiles, formatBytes } from '../api';

function Duplicates() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedFiles, setSelectedFiles] = useState({});
  const [showConfirm, setShowConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadDuplicates();
  }, []);

  const loadDuplicates = async () => {
    try {
      const result = await getDuplicates();
      setData(result);

      // Pre-select files to delete (all except recommended)
      const selected = {};
      result.groups?.forEach(group => {
        group.files.forEach(file => {
          if (!file.is_recommended) {
            selected[file.path] = true;
          }
        });
      });
      setSelectedFiles(selected);
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

    // SAFETY: Extra confirmation for large deletions
    if (pathsToDelete.length > 50) {
      const reallyConfirm = window.confirm(
        `⚠️ WARNING: You are about to delete ${pathsToDelete.length} files!\n\n` +
        `This is a LARGE deletion. Are you absolutely sure?\n\n` +
        `Click OK to proceed, or Cancel to go back.`
      );
      if (!reallyConfirm) {
        return;
      }
    }

    // SAFETY: Check for 100 file limit
    if (pathsToDelete.length > 100) {
      alert(`⚠️ SAFETY LIMIT: Cannot delete more than 100 files at once.\n\nYou selected ${pathsToDelete.length} files.\n\nPlease delete in smaller batches for safety.`);
      return;
    }

    try {
      setDeleting(true);
      const result = await deleteFiles(pathsToDelete, true);

      if (result.failed_count > 0) {
        alert(
          `Deletion completed:\n\n` +
          `✅ Successfully deleted: ${result.deleted_count} files\n` +
          `❌ Failed: ${result.failed_count} files\n\n` +
          `Check the console for details about failed deletions.`
        );
        console.error('Failed deletions:', result.failed);
      } else {
        alert(`✅ Successfully deleted ${result.deleted_count} files!`);
      }

      if (result.deleted_count > 0) {
        loadDuplicates(); // Reload data
      }

      setShowConfirm(false);
    } catch (error) {
      console.error('Failed to delete files:', error);
      alert(`❌ Error: ${error.message}\n\nNo files were deleted. Please try again.`);
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
            Delete Selected
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
                {formatBytes(group.total_size)} total • Can save {formatBytes(group.space_can_save)}
              </p>
            </div>
          </div>

          <div className="group-files">
            {group.files.map((file) => (
              <div
                key={file.path}
                className={`group-file-item ${file.is_recommended ? 'recommended' : ''}`}
              >
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

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>⚠️ Confirm Deletion</h2>
            </div>
            <div>
              <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                Are you sure you want to delete {selectedCount} files?
              </p>
              <p className="text-secondary text-small mt-2">
                This will free up {formatBytes(selectedSize)} of space.
              </p>
              <div style={{
                backgroundColor: 'var(--bg-tertiary)',
                padding: '1rem',
                borderRadius: 'var(--radius-sm)',
                marginTop: '1rem',
                border: '2px solid var(--accent-red)'
              }}>
                <p className="text-small" style={{ color: 'var(--accent-red)', fontWeight: 600 }}>
                  ⚠️ THIS ACTION CANNOT BE UNDONE!
                </p>
                <p className="text-small mt-2">
                  The files will be permanently deleted from your Dropbox.
                </p>
                {selectedCount > 20 && (
                  <p className="text-small mt-2" style={{ color: 'var(--accent-yellow)', fontWeight: 600 }}>
                    ⚠️ Large deletion: {selectedCount} files
                  </p>
                )}
              </div>
              <p className="text-small text-secondary mt-2">
                ℹ️ Recommended files (highlighted in green) are protected and will NOT be deleted.
              </p>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => setShowConfirm(false)}
                disabled={deleting}
              >
                Cancel - Don't Delete
              </button>
              <button
                className="btn-danger"
                onClick={handleDeleteSelected}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : `Yes, Delete ${selectedCount} Files`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Duplicates;
