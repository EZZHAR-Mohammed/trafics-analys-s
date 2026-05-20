// src/pages/VideoProcess.js
// Page de traitement vidéo.
// L'utilisateur upload une vidéo, choisit des paramètres puis lance l'analyse.
import React, { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import {
  Upload, Film, Settings, Play, CheckCircle,
  AlertTriangle, X, ChevronDown, ChevronUp,
} from 'lucide-react';
import { uploadVideo, processVideo } from '../services/api';

const DEFAULT_PARAMS = {
  method: 'both',
  enable_tracking: true,
  enable_alerts: true,
  save_output: true,
  speed_alert_threshold: 15,
  motion_threshold: 2.0,
  max_frames: 300,
};

export default function VideoProcess() {
  const [file, setFile]         = useState(null);
  const [uploaded, setUploaded] = useState(null);   // { filename, metadata }
  const [params, setParams]     = useState(DEFAULT_PARAMS);
  const [phase, setPhase]       = useState('idle'); // idle | uploading | processing | done | error
  const [progress, setProgress] = useState(0);
  const [showAdv, setShowAdv]   = useState(false);

  const onDrop = useCallback(accepted => {
    if (accepted.length > 0) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/*': ['.mp4', '.avi', '.mov', '.mkv', '.webm'] },
    maxFiles: 1,
  });

  const handleUpload = async () => {
    if (!file) return;
    setPhase('uploading');
    setProgress(0);
    try {
      // Envoi du fichier vers le backend FastAPI.
      const r = await uploadVideo(file, p => setProgress(p));
      setUploaded(r.data);
      setPhase('ready');
      toast.success(`Vidéo uploadée: ${r.data.filename}`);
    } catch (e) {
      setPhase('error');
      toast.error(`Upload échoué: ${e.response?.data?.detail || e.message}`);
    }
  };

  const handleProcess = async () => {
    if (!uploaded) return;
    setPhase('processing');
    try {
      // Envoie au backend la requête de traitement vidéo.
      const r = await processVideo(uploaded.filename, params);
      setPhase('done');
      toast.success(`✅ Traitement terminé — ${r.data.processed_frames} frames`);
    } catch (e) {
      setPhase('error');
      toast.error(`Traitement échoué: ${e.response?.data?.detail || e.message}`);
    }
  };

  const reset = () => {
    setFile(null); setUploaded(null);
    setPhase('idle'); setProgress(0);
  };

  const set = (k, v) => setParams(p => ({ ...p, [k]: v }));

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Traitement Vidéo</h1>
        <p className="page-subtitle">Upload → Paramétrage → Analyse par flot optique</p>
      </div>

      <div className="grid-2" style={{ gap: 20, alignItems: 'start' }}>
        {/* Left column — upload + params */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Dropzone */}
          <div className="card" style={{ padding: 20 }}>
            <div className="section-title">Fichier vidéo</div>
            {phase === 'idle' && (
              <>
                <div
                  {...getRootProps()}
                  className={`dropzone ${isDragActive ? 'drag-active' : ''}`}
                >
                  <input {...getInputProps()} />
                  <Upload size={32} color="var(--cyan)" style={{ opacity: 0.6 }} />
                  {isDragActive
                    ? <p>Déposez le fichier ici...</p>
                    : <p>Glissez-déposez une vidéo<br /><span style={{ color: 'var(--text-muted)', fontSize: 12 }}>MP4, AVI, MOV, MKV — ou cliquez pour parcourir</span></p>
                  }
                </div>
                {file && (
                  <div className="file-preview">
                    <Film size={14} color="var(--cyan)" />
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                    <button className="btn btn-ghost btn-sm" onClick={reset}><X size={12} /></button>
                    <button className="btn btn-primary btn-sm" onClick={handleUpload}>
                      <Upload size={13} /> Upload
                    </button>
                  </div>
                )}
              </>
            )}
            {phase === 'uploading' && (
              <div style={{ padding: '20px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                  <span>Upload en cours...</span>
                  <span className="mono">{progress}%</span>
                </div>
                <div className="progress-bar"><div className="progress-bar-fill" style={{ width: `${progress}%` }} /></div>
              </div>
            )}
            {(phase === 'ready' || phase === 'processing' || phase === 'done') && uploaded && (
              <div className="uploaded-info">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <CheckCircle size={15} color="var(--green)" />
                  <span style={{ fontWeight: 600, color: 'var(--green)', fontSize: 13 }}>Vidéo chargée</span>
                  <button className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto' }} onClick={reset}>
                    <X size={12} /> Changer
                  </button>
                </div>
                <div className="meta-grid">
                  {[
                    ['Fichier',    uploaded.filename?.slice(0,20) + '...'],
                    ['Taille',     `${uploaded.size_mb} MB`],
                    ['FPS',        uploaded.metadata?.fps?.toFixed(1)],
                    ['Frames',     uploaded.metadata?.total_frames],
                    ['Résolution', `${uploaded.metadata?.width}×${uploaded.metadata?.height}`],
                    ['Durée',      `${uploaded.metadata?.duration_sec}s`],
                  ].map(([k, v]) => (
                    <div key={k} className="meta-item">
                      <span className="meta-key">{k}</span>
                      <span className="meta-val mono">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Params */}
          {(phase === 'ready' || phase === 'done') && (
            <div className="card" style={{ padding: 20 }}>
              <div className="section-title">Paramètres</div>

              {/* Method */}
              <div style={{ marginBottom: 16 }}>
                <label className="form-label">Méthode</label>
                <div className="method-tabs">
                  {['lucas_kanade','farneback','both'].map(m => (
                    <button
                      key={m}
                      className={`method-tab ${params.method === m ? 'active' : ''}`}
                      onClick={() => set('method', m)}
                    >
                      {m === 'lucas_kanade' ? 'Lucas-Kanade' : m === 'farneback' ? 'Farneback' : 'Les deux'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Toggles */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
                {[
                  ['enable_tracking', 'Tracking véhicules'],
                  ['enable_alerts',   'Alertes de mouvement'],
                  ['save_output',     'Sauvegarder la vidéo annotée'],
                ].map(([k, label]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{label}</span>
                    <label className="toggle">
                      <input type="checkbox" checked={params[k]} onChange={e => set(k, e.target.checked)} />
                      <span className="toggle-slider" />
                    </label>
                  </div>
                ))}
              </div>

              {/* Advanced */}
              <button className="btn btn-ghost btn-sm" style={{ width: '100%', justifyContent: 'space-between' }}
                onClick={() => setShowAdv(!showAdv)}>
                <span><Settings size={13} /> Paramètres avancés</span>
                {showAdv ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </button>

              {showAdv && (
                <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {[
                    { k: 'max_frames',            label: 'Max frames',              min: 10,  max: 5000, step: 10  },
                    { k: 'speed_alert_threshold', label: 'Seuil vitesse (px/frame)',min: 1,   max: 100,  step: 1   },
                    { k: 'motion_threshold',      label: 'Seuil mouvement',         min: 0.1, max: 20,   step: 0.1 },
                  ].map(({ k, label, min, max, step }) => (
                    <div key={k}>
                      <label className="form-label">{label} — <span className="mono" style={{ color: 'var(--cyan)' }}>{params[k]}</span></label>
                      <input type="range" min={min} max={max} step={step} value={params[k]}
                        onChange={e => set(k, parseFloat(e.target.value))}
                        style={{ width: '100%', accentColor: 'var(--cyan)' }} />
                    </div>
                  ))}
                </div>
              )}

              <button
                className="btn btn-primary"
                style={{ width: '100%', marginTop: 18, padding: '12px' }}
                onClick={handleProcess}
                disabled={phase === 'processing'}
              >
                {phase === 'processing'
                  ? <><div className="spinner" /> Traitement en cours...</>
                  : <><Play size={16} /> Lancer l'analyse</>
                }
              </button>
            </div>
          )}
        </div>

        {/* Right column — result */}
        <div>
          {phase === 'done' && (
            <div
              className="card"
              style={{
                padding: 20,
                borderColor: 'rgba(0,212,255,0.35)',
                background: 'rgba(0,212,255,0.07)',
              }}
            >
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <CheckCircle size={22} color="var(--green)" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <p style={{ margin: '0 0 12px', fontSize: 15, color: 'var(--text-primary)', fontWeight: 600 }}>
                    Traitement terminé
                  </p>
                  <p style={{ margin: '0 0 14px', fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    Pour consulter les <strong>statistiques</strong>, la <strong>direction</strong> des objets suivis, les{' '}
                    <strong>alertes</strong> et la <strong>comparaison des méthodes</strong>, ouvrez la page Résultats.
                  </p>
                  <Link to="/results" className="btn btn-primary">
                    Ouvrir la page Résultats
                  </Link>
                </div>
              </div>
            </div>
          )}
          {phase === 'processing' && (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <div className="spinner" style={{ width: 48, height: 48, margin: '0 auto 20px', borderWidth: 4 }} />
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
                Analyse en cours...
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                Lucas-Kanade + Farneback — tracking + alertes
              </p>
            </div>
          )}
          {phase === 'idle' && (
            <div className="card empty-state">
              <Film size={40} className="empty-state-icon" />
              <p>Uploadez une vidéo et configurez les paramètres pour commencer l'analyse</p>
            </div>
          )}
          {phase === 'error' && (
            <div className="card" style={{ padding: 24, borderColor: 'rgba(255,59,92,0.3)' }}>
              <div style={{ display: 'flex', gap: 10, color: 'var(--red)' }}>
                <AlertTriangle size={20} />
                <div>
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>Erreur de traitement</div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Vérifiez que l'API backend est démarrée sur le port 8000.</p>
                </div>
              </div>
              <button className="btn btn-ghost" style={{ marginTop: 14 }} onClick={reset}>Réessayer</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
