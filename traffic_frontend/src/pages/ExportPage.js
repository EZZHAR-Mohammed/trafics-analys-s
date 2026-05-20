// src/pages/ExportPage.js
// Page d'export des résultats de traitement.
// Offre des liens pour télécharger JSON, CSV, vidéo ou ZIP des frames.
import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Download, FileJson, FileText, Film, RefreshCw } from 'lucide-react';
import { listJobs, exportJson, exportTracksCsv, exportAlertsCsv, exportFramesCsv, downloadVideo, exportFramesZip } from '../services/api';

const EXPORTS = [
  { icon: FileJson, label: 'Résultats JSON',     desc: 'Export complet du job (sans données frames)',  color: 'cyan',   fn: exportJson,      ext: '.json' },
  { icon: FileText, label: 'Tracks CSV',          desc: 'Trajectoires des véhicules',                  color: 'green',  fn: exportTracksCsv, ext: '_tracks.csv' },
  { icon: FileText, label: 'Alertes CSV',         desc: 'Toutes les alertes détectées',                color: 'orange', fn: exportAlertsCsv, ext: '_alerts.csv' },
  { icon: FileText, label: 'Données frames CSV',  desc: 'Métriques par frame (peut être volumineux)',  color: 'purple', fn: exportFramesCsv, ext: '_frames.csv' },
  { icon: Download, label: 'Télécharger frames ZIP', desc: 'Toutes les frames annotées en JPG dans un ZIP', color: 'cyan', fn: exportFramesZip, ext: '_frames.zip' },
  { icon: Film,     label: 'Vidéo annotée',       desc: 'Vidéo avec overlay flot optique et tracking', color: 'red',    fn: downloadVideo,   ext: '_output.mp4' },
];

export default function ExportPage() {
  const [jobs, setJobs]   = useState([]);
  const [jobId, setJobId] = useState('');

  useEffect(() => {
    listJobs().then(r => {
      const done = r.data.filter(j => j.status === 'done');
      setJobs(done);
      if (done.length > 0) setJobId(done[done.length - 1].job_id);
    }).catch(() => {});
  }, []);

  const doExport = (fn, label) => {
    if (!jobId) return toast.error('Sélectionnez un job');
    const url = fn(jobId);
    window.open(url, '_blank');
    toast.success(`Téléchargement: ${label}`);
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Export des données</h1>
        <p className="page-subtitle">Téléchargez les résultats en JSON, CSV ou vidéo annotée</p>
      </div>

      {/* Job selector */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: 24, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <label className="form-label" style={{ margin: 0 }}>Job à exporter</label>
        <select className="input" style={{ maxWidth: 340 }} value={jobId} onChange={e => setJobId(e.target.value)}>
          <option value="">— Choisir un job terminé —</option>
          {jobs.map(j => <option key={j.job_id} value={j.job_id}>Job {j.job_id}</option>)}
        </select>
        <button className="btn btn-ghost btn-sm" onClick={() => listJobs().then(r => setJobs(r.data.filter(j => j.status === 'done'))).catch(() => {})}>
          <RefreshCw size={13} /> Rafraîchir
        </button>
      </div>

      <div className="grid-auto" style={{ gap: 16 }}>
        {EXPORTS.map(({ icon: Icon, label, desc, color, fn }) => (
          <div key={label} className="card" style={{ padding: 22, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{
              width: 46, height: 46,
              background: `var(--${color}-dim)`,
              border: `1px solid rgba(var(--${color}-rgb, 0,0,0), 0.2)`,
              borderRadius: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Icon size={20} color={`var(--${color})`} />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{label}</div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.4 }}>{desc}</p>
            </div>
            <button
              className="btn btn-ghost"
              style={{ marginTop: 'auto', justifyContent: 'center' }}
              onClick={() => doExport(fn, label)}
              disabled={!jobId}
            >
              <Download size={14} /> Télécharger
            </button>
          </div>
        ))}
      </div>

      {jobs.length === 0 && (
        <div className="card empty-state" style={{ marginTop: 24 }}>
          <Download size={40} className="empty-state-icon" />
          <p>Aucun job terminé trouvé. Traitez d'abord une vidéo dans l'onglet "Vidéo".</p>
        </div>
      )}
    </div>
  );
}
