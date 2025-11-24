import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const checkConnection = async () => {
  const response = await api.get('/connection');
  return response.data;
};

export const startScan = async (path = '', recursive = true, analyzeImages = true) => {
  const response = await api.post('/scan', {
    path,
    recursive,
    analyze_images: analyzeImages,
  });
  return response.data;
};

export const getJobStatus = async (jobId) => {
  const response = await api.get(`/jobs/${jobId}`);
  return response.data;
};

export const getStats = async () => {
  const response = await api.get('/stats');
  return response.data;
};

export const getDuplicates = async () => {
  const response = await api.get('/duplicates');
  return response.data;
};

export const getSimilar = async () => {
  const response = await api.get('/similar');
  return response.data;
};

export const getFiles = async (path = '', limit = 100, offset = 0) => {
  const response = await api.get('/files', {
    params: { path, limit, offset },
  });
  return response.data;
};

export const deleteFiles = async (paths, confirm = false) => {
  const response = await api.post('/delete', {
    paths,
    confirm,
  });
  return response.data;
};

export const renameFiles = async (operations, confirm = false) => {
  const response = await api.post('/rename', {
    operations,
    confirm,
  });
  return response.data;
};

export const getNamingSuggestions = async (limit = 50) => {
  const response = await api.get('/naming/suggestions', {
    params: { limit },
  });
  return response.data;
};

export const getImageUrl = (path, thumb = true) => {
  if (!path) return '';
  const params = new URLSearchParams({ path, thumb: thumb ? 'true' : 'false' });
  return `${API_BASE}/image?${params.toString()}`;
};

export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

export default api;
