import React, { useState, useEffect } from 'react';
import { getFiles, getNamingSuggestions, renameFiles, formatBytes } from '../api';

function Files() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [suggestions, setSuggestions] = useState([]);
  const [showRename, setShowRename] = useState(false);
  const [selectedRenames, setSelectedRenames] = useState({});

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const result = await getFiles('', 100, 0);
      setFiles(result.files);
    } catch (error) {
      console.error('Failed to load files:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSuggestions = async () => {
    try {
      const result = await getNamingSuggestions(50);
      setSuggestions(result.suggestions);
      setShowRename(true);

      // Pre-select all suggestions
      const selected = {};
      result.suggestions.forEach(s => {
        selected[s.path] = true;
      });
      setSelectedRenames(selected);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const handleRename = async () => {
    const operations = suggestions
      .filter(s => selectedRenames[s.path])
      .map(s => ({
        from: s.path,
        to: s.path.replace(s.current_name, s.suggested_name)
      }));

    if (operations.length === 0) {
      alert('No files selected');
      return;
    }

    try {
      const result = await renameFiles(operations, true);
      alert(`Renamed ${result.renamed_count} files. Failed: ${result.failed_count}`);

      if (result.renamed_count > 0) {
        loadFiles();
        setShowRename(false);
      }
    } catch (error) {
      console.error('Failed to rename files:', error);
      alert('Failed to rename files: ' + error.message);
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
        <div className="flex justify-between items-center">
          <div>
            <h1>All Files</h1>
            <p className="text-secondary">{files.length} files in cache</p>
          </div>
          <button className="btn-primary" onClick={loadSuggestions}>
            Get Naming Suggestions
          </button>
        </div>
      </div>

      {/* File List */}
      <div className="file-list">
        {files.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📁</div>
            <h3>No Files</h3>
            <p>Run a scan to populate the file cache</p>
          </div>
        ) : (
          files.map((file) => (
            <div key={file.path} className="file-item">
              <div className="file-icon">
                {file.is_image ? '🖼️' : '📄'}
              </div>
              <div className="file-info">
                <div className="file-name">{file.name}</div>
                <div className="file-meta">
                  {file.path} • {formatBytes(file.size)}
                  {file.quality_score && (
                    <span style={{ marginLeft: '0.5rem' }}>
                      • Quality: {Math.round(file.quality_score)}%
                    </span>
                  )}
                </div>
                {file.suggested_name && (
                  <div className="text-small" style={{ color: 'var(--accent-blue)' }}>
                    Suggested: {file.suggested_name}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Rename Modal */}
      {showRename && (
        <div className="modal-overlay" onClick={() => setShowRename(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>File Naming Suggestions</h2>
              <p className="text-secondary text-small">
                {suggestions.length} files with suggested improvements
              </p>
            </div>
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {suggestions.map((suggestion) => (
                <div
                  key={suggestion.path}
                  style={{
                    padding: '0.75rem',
                    borderBottom: '1px solid var(--border-color)',
                  }}
                >
                  <div className="flex items-center gap-4">
                    <input
                      type="checkbox"
                      checked={selectedRenames[suggestion.path] || false}
                      onChange={() =>
                        setSelectedRenames(prev => ({
                          ...prev,
                          [suggestion.path]: !prev[suggestion.path]
                        }))
                      }
                    />
                    <div style={{ flex: 1 }}>
                      <div className="text-small text-secondary" style={{ textDecoration: 'line-through' }}>
                        {suggestion.original}
                      </div>
                      <div className="file-name" style={{ color: 'var(--accent-green)' }}>
                        {suggestion.suggested}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => setShowRename(false)}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleRename}
              >
                Rename Selected ({Object.values(selectedRenames).filter(Boolean).length})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Files;
