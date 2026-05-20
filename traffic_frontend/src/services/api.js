// src/services/api.js
// Client HTTP centralisé du frontend.
// Toutes les requêtes vers le backend FastAPI passent par ce module.
import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE,
  timeout: 300000,
});

// ── Video ──────────────────────────────────────────────
// Routes pour uploader une vidéo, lancer le traitement et récupérer les jobs.
export const uploadVideo = (file, onProgress) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/api/v1/video/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  });
};

export const processVideo = (filename, params) =>
  api.post(`/api/v1/video/process?filename=${filename}&run_async=false`, params);

export const listJobs = () => api.get('/api/v1/video/jobs');
export const getJob = (id) => api.get(`/api/v1/video/jobs/${id}`);
export const analyzeFrame = (filename, frameNumber, method = 'both') =>
  api.get(`/api/v1/video/frame/${filename}?frame_number=${frameNumber}&method=${method}`);
export const getAnnotatedFrame = (filename, frameNumber, method = 'both') =>
  api.get(`/api/v1/video/frame/${filename}/annotated?frame_number=${frameNumber}&method=${method}`);

// ── Camera ────────────────────────────────────────────
export const listCameras = () => api.get('/api/v1/camera/list');
export const cameraSnapshot = (index = 0, method = 'both') =>
  api.get(`/api/v1/camera/snapshot?camera_index=${index}&method=${method}`);
export const processCameraFrames = (params) =>
  api.post(`/api/v1/camera/process-frames?camera_index=${params.camera_index}&n_frames=${params.n_frames}&method=${params.method}&motion_threshold=${params.motion_threshold}&speed_threshold=${params.speed_threshold}`);
export const getStreamStatus = () => api.get('/api/v1/camera/stream/status');
export const stopStream = () => api.post('/api/v1/camera/stream/stop');
export const saveCameraSession = (format = 'json') =>
  api.post(`/api/v1/camera/save-session?format=${format}`, null, { responseType: 'blob' });
export const getStreamUrl = (index = 0, method = 'both') =>
  `${BASE}/api/v1/camera/stream?camera_index=${index}&method=${method}`;

// ── Analysis ──────────────────────────────────────────
export const getAnalysisSummary = (id) => api.get(`/api/v1/analysis/${id}/summary`);
export const compareMethods = (id) => api.get(`/api/v1/analysis/${id}/compare-methods`);
export const getSpeedDistribution = (id, bins = 10) =>
  api.get(`/api/v1/analysis/${id}/speed-distribution?bins=${bins}`);
export const getFrameData = (id, start = 0, end = 200) =>
  api.get(`/api/v1/analysis/${id}/frame-data?start=${start}&end=${end}`);

// ── Tracking ──────────────────────────────────────────
export const getTracks = (id) => api.get(`/api/v1/tracking/${id}/tracks`);
export const getFastVehicles = (id, threshold = 15) =>
  api.get(`/api/v1/tracking/${id}/fast-vehicles?threshold=${threshold}`);

// ── Alerts ───────────────────────────────────────────
export const getAlerts = (id) => api.get(`/api/v1/alerts/${id}/all`);
export const getAlertTimeline = (id) => api.get(`/api/v1/alerts/${id}/timeline`);

// ── Export ────────────────────────────────────────────
export const exportJson = (id) => `${BASE}/api/v1/export/${id}/json`;
export const exportTracksCsv = (id) => `${BASE}/api/v1/export/${id}/csv/tracks`;
export const exportAlertsCsv = (id) => `${BASE}/api/v1/export/${id}/csv/alerts`;
export const exportFramesCsv = (id) => `${BASE}/api/v1/export/${id}/csv/frames`;
export const downloadVideo = (id) => `${BASE}/api/v1/export/${id}/video`;
export const exportFramesZip = (id) => `${BASE}/api/v1/export/${id}/frames-zip`;

// ── Health ────────────────────────────────────────────
export const healthCheck = () => api.get('/health');

export default api;
