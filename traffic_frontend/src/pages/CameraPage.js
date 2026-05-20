// src/pages/CameraPage.js
// Page de démonstration de caméra live.
// Elle affiche le flux MJPEG et permet de capturer des snapshots et d'exporter la session.
import React, { useState, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { Camera, Play, Square, Download } from 'lucide-react';
import { listCameras, cameraSnapshot, getStreamStatus, stopStream, getStreamUrl, saveCameraSession } from '../services/api';

export default function CameraPage() {
  const [cameras, setCameras] = useState([]);
  const [camIndex, setCamIndex] = useState(0);
  const [method, setMethod] = useState('both');
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [snapLoading, setSnapLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [streamHasFrames, setStreamHasFrames] = useState(false);
  const imgRef = useRef(null);
  const statusTimer = useRef(null);

  useEffect(() => {
    // Recherche de caméras disponibles au chargement de la page.
    listCameras().then(r => setCameras(r.data.cameras || [])).catch(() => {});
    return () => {
      clearInterval(statusTimer.current);
    };
  }, []);

  const startStream = () => {
    setStreamHasFrames(false);
    setStreaming(true);
    const url = getStreamUrl(camIndex, method);
    if (imgRef.current) imgRef.current.src = url;
    statusTimer.current = setInterval(async () => {
      try {
        const r = await getStreamStatus();
        setStatus(r.data);
        if (r.data?.frame_count > 0) setStreamHasFrames(true);
      } catch {
        /* ignore */
      }
    }, 1500);
    toast.success('Flux démarré');
  };

  const stopStreamFn = async () => {
    try {
      await stopStream();
    } catch {
      /* ignore */
    }
    setStreaming(false);
    if (imgRef.current) imgRef.current.src = '';
    clearInterval(statusTimer.current);
    setStatus(null);
    toast('Flux arrêté');
    /* streamHasFrames laissé vrai si des images ont été enregistrées : export CSV encore possible */
  };

  const takeSnapshot = async () => {
    setSnapLoading(true);
    try {
      // Capture une image unique et demande le traitement optique.
      const r = await cameraSnapshot(camIndex, method);
      setSnapshot(r.data);
      toast.success('Image capturée');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Caméra indisponible');
    } finally {
      setSnapLoading(false);
    }
  };

  const downloadSessionCsv = async () => {
    setCsvLoading(true);
    try {
      const r = await saveCameraSession('csv');
      const blob = new Blob([r.data], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `camera_live_${camIndex}_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success('CSV téléchargé (données du flux en direct)');
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Téléchargement impossible';
      toast.error(typeof msg === 'string' ? msg : 'Données insuffisantes — laissez le flux tourner quelques secondes.');
    } finally {
      setCsvLoading(false);
    }
  };

  const downloadSnapshotImage = (base64Image, filename) => {
    if (!base64Image) return;
    const a = document.createElement('a');
    a.href = `data:image/jpeg;base64,${base64Image}`;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const statusLine =
    streaming && status
      ? [
          status.fps != null && `${Number(status.fps).toFixed(1)} FPS`,
          status.frame_count != null && `${status.frame_count} images`,
          status.active_tracks != null && `${status.active_tracks} pistes`,
        ]
          .filter(Boolean)
          .join(' · ')
      : null;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Caméra Live</h1>
        <p className="page-subtitle">Aperçu webcam avec analyse en direct</p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 960, margin: '0 auto' }}>
        <div className="card" style={{ overflow: 'hidden' }}>
          <div
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              flexWrap: 'wrap',
            }}
          >
            {streaming && <div className="dot-live" />}
            <span style={{ fontWeight: 600, fontSize: 14 }}>Flux</span>
            {statusLine && (
              <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                {statusLine}
              </span>
            )}
          </div>
          <div
            style={{
              position: 'relative',
              background: '#000',
              minHeight: 280,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <img
              ref={imgRef}
              alt="Flux webcam"
              style={{
                width: '100%',
                display: streaming ? 'block' : 'none',
                maxHeight: 520,
                objectFit: 'contain',
              }}
            />
            {!streaming && (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 36 }}>
                <Camera size={40} style={{ opacity: 0.25, marginBottom: 10 }} />
                <p style={{ fontSize: 14, margin: 0 }}>Démarrez le flux pour afficher la caméra</p>
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 12,
              alignItems: 'flex-end',
            }}
          >
            <div style={{ flex: '1 1 160px', minWidth: 0 }}>
              <label className="form-label">Caméra</label>
              <select className="input" value={camIndex} onChange={e => setCamIndex(Number(e.target.value))} disabled={streaming}>
                {cameras.length === 0 ? (
                  <option value={0}>Caméra 0</option>
                ) : (
                  cameras.map(c => (
                    <option key={c.index} value={c.index}>
                      {c.index} — {c.width}×{c.height}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div style={{ flex: '1 1 140px', minWidth: 0 }}>
              <label className="form-label">Méthode</label>
              <select className="input" value={method} onChange={e => setMethod(e.target.value)} disabled={streaming}>
                <option value="both">Les deux</option>
                <option value="lucas_kanade">Lucas-Kanade</option>
                <option value="farneback">Farneback</option>
              </select>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
              {!streaming ? (
                <button type="button" className="btn btn-primary" onClick={startStream}>
                  <Play size={15} /> Démarrer
                </button>
              ) : (
                <button type="button" className="btn btn-danger" onClick={stopStreamFn}>
                  <Square size={15} /> Arrêter
                </button>
              )}
              {(streaming || streamHasFrames) && (
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={downloadSessionCsv}
                  disabled={csvLoading || (streaming && !streamHasFrames)}
                  title={
                    streaming && !streamHasFrames
                      ? 'Attendez quelques images du flux'
                      : 'CSV : une ligne par image (FPS, pistes, mouvement, alertes…)'
                  }
                >
                  {csvLoading ? (
                    <>
                      <div className="spinner" /> …
                    </>
                  ) : (
                    <>
                      <Download size={15} /> Télécharger CSV
                    </>
                  )}
                </button>
              )}
              <button type="button" className="btn btn-ghost" onClick={takeSnapshot} disabled={snapLoading}>
                {snapLoading ? (
                  <>
                    <div className="spinner" /> …
                  </>
                ) : (
                  <>
                    <Camera size={15} /> Capture
                  </>
                )}
              </button>
            </div>
            {(streaming || streamHasFrames) && (
              <p style={{ margin: '12px 0 0', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.45 }}>
                Le CSV reprend les données du flux (comme la ligne d’état au-dessus de la vidéo) : numéro d’image, temps, FPS, caméra, méthode,
                intensité du mouvement, pistes actives, vitesse max des pistes, alerte oui/non. Téléchargez après quelques secondes de flux, ou
                après avoir arrêté.
              </p>
            )}
          </div>
        </div>

        {snapshot && (
          <div className="card" style={{ padding: 16 }}>
            <div className="section-title" style={{ marginBottom: 12 }}>
              Dernière capture
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
              {snapshot.lk_frame_b64 && (
                <div>
                  <div className="badge badge-cyan" style={{ marginBottom: 8 }}>
                    Lucas-Kanade
                  </div>
                  <img src={`data:image/jpeg;base64,${snapshot.lk_frame_b64}`} alt="LK" style={{ width: '100%', borderRadius: 8 }} />
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    style={{ marginTop: 8 }}
                    onClick={() => downloadSnapshotImage(snapshot.lk_frame_b64, `capture_lk_${camIndex}.jpg`)}
                  >
                    Télécharger
                  </button>
                </div>
              )}
              {snapshot.fb_frame_b64 && (
                <div>
                  <div className="badge badge-orange" style={{ marginBottom: 8 }}>
                    Farneback
                  </div>
                  <img src={`data:image/jpeg;base64,${snapshot.fb_frame_b64}`} alt="FB" style={{ width: '100%', borderRadius: 8 }} />
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    style={{ marginTop: 8 }}
                    onClick={() => downloadSnapshotImage(snapshot.fb_frame_b64, `capture_fb_${camIndex}.jpg`)}
                  >
                    Télécharger
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
