// src/pages/ResultsPage.js
// Page des résultats : affichage des jobs traités, statistiques, pistes et alertes.
import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import {
  BarChart2,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  RefreshCw,
  Film,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  listJobs,
  getAnalysisSummary,
  getTracks,
  getAlerts,
  compareMethods,
  downloadVideo,
} from '../services/api';

const ALERT_LABELS = {
  high_motion: 'Mouvement important',
  fast_vehicle: 'Déplacement très rapide',
  motion_spike: 'Pic d’activité',
  sudden_stop: 'Ralentissement marqué',
  congestion: 'Encombrement possible',
};

function alertLabel(type) {
  return ALERT_LABELS[type] || type.replace(/_/g, ' ');
}

function formatJobDate(ts) {
  if (ts == null) return '';
  const ms = ts < 1e12 ? ts * 1000 : ts;
  return new Date(ms).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
}

function methodLabel(m) {
  if (m === 'both') return 'Les deux méthodes';
  if (m === 'lucas_kanade') return 'Lucas-Kanade';
  if (m === 'farneback') return 'Farneback';
  return m || '—';
}

/** Angle atan2(dy,dx) en ° : 0° = vers la droite, 90° = vers le bas sur l’image */
function formatDirection(deg) {
  if (deg == null || Number.isNaN(Number(deg))) return '—';
  const d = ((Number(deg) % 360) + 360) % 360;
  const rose = ['E', 'SE', 'S', 'SO', 'O', 'NO', 'N', 'NE'];
  const idx = Math.round(d / 45) % 8;
  return `${d.toFixed(0)}° (${rose[idx]})`;
}

function StatBlock({ title, color, rows }) {
  if (!rows?.length) return null;
  return (
    <div style={{ padding: 12, borderRadius: 8, border: '1px solid var(--border)', borderTop: `3px solid var(--${color})` }}>
      <div style={{ fontWeight: 700, fontSize: 13, color: `var(--${color})`, marginBottom: 10 }}>{title}</div>
      {rows.map(([label, val]) => (
        <div key={label} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{label}</span>
          <span className="mono" style={{ fontSize: 12, color: `var(--${color})` }}>
            {val}
          </span>
        </div>
      ))}
    </div>
  );
}

const ChartTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 8,
        fontSize: 11,
        fontFamily: 'var(--font-mono)',
      }}
    >
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Image {label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  );
};

export default function ResultsPage() {
  const [jobs, setJobs] = useState([]);
  const [jobId, setJobId] = useState('');
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [tracks, setTracks] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [tracksTab, setTracksTab] = useState('liste');

  const refreshJobList = () => {
    listJobs()
      .then(r => {
        const done = r.data.filter(j => j.status === 'done');
        setJobs(done);
        if (done.length && !jobId) setJobId(done[done.length - 1].job_id);
      })
      .catch(() => {});
  };

  useEffect(() => {
    // Charge la liste des résultats disponibles au démarrage.
    refreshJobList();
  }, []);

  const load = async id => {
    if (!id) return;
    setLoading(true);
    setSummary(null);
    setTracks([]);
    setAlerts([]);
    setComparison(null);
    try {
      const [s, tr, al] = await Promise.all([getAnalysisSummary(id), getTracks(id), getAlerts(id)]);
      setSummary(s.data);
      setTracks(tr.data.tracks || []);
      setAlerts(al.data.alerts || []);
      setTracksTab('liste');

      if (s.data.method === 'both') {
        try {
          const c = await compareMethods(id);
          setComparison(c.data);
        } catch {
          setComparison(null);
          toast.error('Comparaison des méthodes indisponible');
        }
      } else {
        setComparison(null);
      }
      toast.success('Données à jour');
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message || 'Chargement impossible');
      setSummary(null);
      setTracks([]);
      setAlerts([]);
      setComparison(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId) load(jobId);
  }, [jobId]);

  const nAlerts = summary?.total_alerts ?? 0;
  const nTracks = tracks.length;
  const nFast = summary?.tracking?.fast_vehicles ?? tracks.filter(t => t.is_fast).length;
  const usedBoth = summary?.method === 'both';
  const sample = comparison?.frame_comparison_sample || [];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Résultats</h1>
        <p className="page-subtitle">
          Dans la liste des résultats, choisissez celui que vous voulez afficher : le résumé et le détail s’ouvrent à droite.
        </p>
      </div>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 20,
          maxWidth: 980,
          margin: '0 auto',
          alignItems: 'flex-start',
        }}
      >
        {/* Liste des résultats (sélection pour affichage) */}
        <aside
          className="card"
          style={{
            flex: '0 1 280px',
            padding: 0,
            overflow: 'hidden',
            alignSelf: 'stretch',
            minWidth: 220,
          }}
        >
          <div
            style={{
              padding: '14px 16px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <div style={{ flex: 1 }}>
              <div className="section-title" style={{ marginBottom: 2 }}>
                Liste des résultats
              </div>
              <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)' }}>Un résultat = une vidéo déjà traitée</p>
            </div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={refreshJobList} title="Rafraîchir les résultats">
              <RefreshCw size={14} />
            </button>
          </div>
          <div style={{ maxHeight: 'min(70vh, 520px)', overflowY: 'auto' }}>
            {jobs.length === 0 ? (
              <p style={{ padding: 16, margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
                Aucun résultat pour l’instant. Lancez un traitement sur la page Vidéo : le résultat apparaîtra ici une fois terminé.
              </p>
            ) : (
              jobs.map(j => {
                const sel = j.job_id === jobId;
                return (
                  <button
                    key={j.job_id}
                    type="button"
                    onClick={() => setJobId(j.job_id)}
                    className="btn btn-ghost"
                    style={{
                      width: '100%',
                      borderRadius: 0,
                      justifyContent: 'flex-start',
                      padding: '12px 14px',
                      borderBottom: '1px solid var(--border)',
                      background: sel ? 'rgba(0,212,255,0.08)' : 'transparent',
                      borderLeft: sel ? '3px solid var(--cyan)' : '3px solid transparent',
                      textAlign: 'left',
                      height: 'auto',
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Résultat</div>
                      <div className="mono" style={{ fontWeight: 600, fontSize: 13, color: sel ? 'var(--cyan)' : 'var(--text-primary)' }}>
                        {j.job_id}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{formatJobDate(j.created_at)}</div>
                    </div>
                    <ChevronRight size={16} color={sel ? 'var(--cyan)' : 'var(--text-muted)'} />
                  </button>
                );
              })
            )}
          </div>
        </aside>

        {/* Détail */}
        <div style={{ flex: '1 1 400px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {!jobId && jobs.length > 0 && (
            <div className="card empty-state" style={{ padding: 28 }}>
              <BarChart2 size={40} className="empty-state-icon" />
              <p style={{ margin: 0 }}>Choisissez un résultat dans la liste à gauche pour voir le détail ici</p>
            </div>
          )}

          {jobId && loading && (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <div className="spinner" style={{ margin: '0 auto' }} />
              <p style={{ marginTop: 14, color: 'var(--text-muted)', fontSize: 14 }}>Chargement…</p>
            </div>
          )}

          {summary && !loading && (
            <>
              <div className="card" style={{ padding: 18 }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                  <div className="section-title" style={{ marginBottom: 0 }}>
                    Résultat <span className="mono" style={{ color: 'var(--cyan)' }}>{summary.job_id}</span>
                  </div>
                  <span className="badge badge-cyan">{methodLabel(summary.method)}</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginLeft: 'auto', alignItems: 'center' }}>
                    {summary.output_video_url ? (
                      <a
                        href={downloadVideo(jobId)}
                        className="btn btn-ghost btn-sm"
                        target="_blank"
                        rel="noopener noreferrer"
                        download
                        title="Télécharger la vidéo annotée (MP4)"
                      >
                        <Film size={15} /> Vidéo annotée (MP4)
                      </a>
                    ) : (
                      <span className="badge" style={{ fontSize: 11, opacity: 0.75 }} title="Lancez le traitement avec l’option « Sauvegarder la vidéo annotée »">
                        Pas de vidéo exportée
                      </span>
                    )}
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => load(jobId)}>
                      Actualiser
                    </button>
                  </div>
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 16px', lineHeight: 1.5 }}>
                  Vue d’ensemble de ce résultat : images traitées, objets suivis et alertes.
                </p>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <li style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Images analysées</span>
                    <strong className="mono" style={{ fontSize: 18, color: 'var(--cyan)' }}>
                      {summary.processed_frames ?? '—'}
                    </strong>
                  </li>
                  <li style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Vitesse de traitement</span>
                    <strong className="mono" style={{ fontSize: 18, color: 'var(--green)' }}>
                      {summary.avg_processing_fps != null ? `${Number(summary.avg_processing_fps).toFixed(1)} img/s` : '—'}
                    </strong>
                  </li>
                  <li style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Objets suivis (pistes)</span>
                    <strong className="mono" style={{ fontSize: 18, color: 'var(--purple)' }}>
                      {nTracks}
                    </strong>
                  </li>
                  <li style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Mouvements très rapides</span>
                    <strong className="mono" style={{ fontSize: 18, color: 'var(--orange)' }}>
                      {nFast}
                    </strong>
                  </li>
                  <li style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Alertes</span>
                    <strong className="mono" style={{ fontSize: 18, color: nAlerts > 0 ? 'var(--red)' : 'var(--text-muted)' }}>
                      {nAlerts}
                    </strong>
                  </li>
                </ul>

                <div
                  style={{
                    marginTop: 18,
                    padding: '12px 14px',
                    borderRadius: 8,
                    background: nAlerts > 0 ? 'rgba(255,59,92,0.08)' : 'rgba(0,255,157,0.06)',
                    border: `1px solid ${nAlerts > 0 ? 'rgba(255,59,92,0.25)' : 'rgba(0,255,157,0.2)'}`,
                    display: 'flex',
                    gap: 10,
                    alignItems: 'flex-start',
                  }}
                >
                  {nAlerts > 0 ? (
                    <AlertTriangle size={18} color="var(--red)" style={{ flexShrink: 0, marginTop: 2 }} />
                  ) : (
                    <CheckCircle size={18} color="var(--green)" style={{ flexShrink: 0, marginTop: 2 }} />
                  )}
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                    {nAlerts > 0
                      ? `${nAlerts} événement(s) à examiner dans la section Alertes.`
                      : 'Aucune alerte : le trafic reste dans les seuils définis.'}
                  </p>
                </div>
              </div>

              <div className="card" style={{ padding: 18 }}>
                <div className="section-title" style={{ marginBottom: 8 }}>
                  Statistiques
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 14px', lineHeight: 1.5 }}>
                  Chiffres agrégés sur toute la vidéo : mouvement, temps de calcul par image, et flot optique (Lucas-Kanade / Farneback) si disponibles.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 14 }}>
                  {summary.motion_events != null && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Images avec mouvement détecté</span>
                      <strong className="mono" style={{ color: 'var(--cyan)' }}>
                        {summary.motion_events}
                      </strong>
                    </div>
                  )}
                  {summary.alert_events != null && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Images ayant déclenché une alerte</span>
                      <strong className="mono" style={{ color: 'var(--orange)' }}>
                        {summary.alert_events}
                      </strong>
                    </div>
                  )}
                  {summary.processing_time && (
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                      <strong style={{ color: 'var(--text-secondary)' }}>Temps de traitement par image :</strong>{' '}
                      moyenne{' '}
                      <span className="mono" style={{ color: 'var(--green)' }}>
                        {summary.processing_time.avg_ms} ms
                      </span>
                      {' · '}
                      min {summary.processing_time.min_ms} ms · max {summary.processing_time.max_ms} ms
                    </div>
                  )}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
                  <StatBlock
                    title="Lucas-Kanade (flot)"
                    color="cyan"
                    rows={
                      summary.lk_statistics
                        ? [
                            ['Magnitude moyenne', summary.lk_statistics.avg_magnitude?.toFixed(3) ?? '—'],
                            ['Magnitude max', summary.lk_statistics.max_magnitude?.toFixed(3) ?? '—'],
                            ['Écart-type', summary.lk_statistics.std_magnitude?.toFixed(3) ?? '—'],
                          ]
                        : null
                    }
                  />
                  <StatBlock
                    title="Farneback (flot)"
                    color="orange"
                    rows={
                      summary.farneback_statistics
                        ? [
                            ['Magnitude moyenne', summary.farneback_statistics.avg_magnitude?.toFixed(3) ?? '—'],
                            ['Magnitude max', summary.farneback_statistics.max_magnitude?.toFixed(3) ?? '—'],
                            ['Écart-type', summary.farneback_statistics.std_magnitude?.toFixed(3) ?? '—'],
                          ]
                        : null
                    }
                  />
                </div>
                {summary.alert_summary?.by_type && Object.keys(summary.alert_summary.by_type).length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: 'var(--text-secondary)' }}>Alertes par type</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {Object.entries(summary.alert_summary.by_type).map(([type, count]) => (
                        <span key={type} className="badge badge-cyan" style={{ fontSize: 12 }}>
                          {alertLabel(type)} : <strong>{count}</strong>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="card" style={{ padding: 18 }}>
                <div className="section-title" style={{ marginBottom: 8 }}>
                  Objets suivis
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 14px', lineHeight: 1.5 }}>
                  {usedBoth
                    ? 'Consultez la liste des trajectoires ou la comparaison entre Lucas-Kanade et Farneback.'
                    : 'Trajectoires détectées sur la vidéo (une seule méthode pour ce résultat).'}
                </p>

                {usedBoth ? (
                  <div className="tab-bar" style={{ marginBottom: 14 }}>
                    <button type="button" className={`tab-btn ${tracksTab === 'liste' ? 'active' : ''}`} onClick={() => setTracksTab('liste')}>
                      Liste des pistes
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${tracksTab === 'comparaison' ? 'active' : ''}`}
                      onClick={() => setTracksTab('comparaison')}
                    >
                      Comparaison LK / Farneback
                    </button>
                  </div>
                ) : null}

                {(!usedBoth || tracksTab === 'liste') && (
                  <>
                    {nTracks === 0 ? (
                      <p style={{ color: 'var(--text-muted)', fontSize: 14, margin: 0 }}>Aucune piste pour ce résultat.</p>
                    ) : (
                      <div className="table-wrapper">
                        <table>
                          <thead>
                            <tr>
                              <th>N°</th>
                              <th>Indice vitesse</th>
                              <th>Direction</th>
                              <th>Statut</th>
                            </tr>
                          </thead>
                          <tbody>
                            {tracks.slice(0, 25).map(t => (
                              <tr key={t.track_id}>
                                <td>
                                  <span className="mono" style={{ color: 'var(--cyan)' }}>
                                    {t.track_id}
                                  </span>
                                </td>
                                <td className="mono">{Number(t.speed_pixels_per_frame).toFixed(1)}</td>
                                <td className="mono" style={{ fontSize: 12 }} title="Angle principal du déplacement sur l’image">
                                  {formatDirection(t.direction_angle_deg)}
                                </td>
                                <td>
                                  {t.is_fast ? (
                                    <span className="badge badge-red">Rapide</span>
                                  ) : (
                                    <span className="badge badge-green">Normal</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {nTracks > 25 && (
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12, marginBottom: 0 }}>
                        25 premières pistes sur {nTracks}.
                      </p>
                    )}
                  </>
                )}

                {usedBoth && tracksTab === 'comparaison' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {!comparison ? (
                      <p style={{ color: 'var(--text-muted)', fontSize: 14, margin: 0 }}>Données de comparaison en cours de chargement ou indisponibles.</p>
                    ) : (
                      <>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
                          <div
                            style={{
                              padding: 14,
                              borderRadius: 10,
                              border: '1px solid var(--border)',
                              borderTop: '3px solid var(--cyan)',
                            }}
                          >
                            <div style={{ fontWeight: 700, color: 'var(--cyan)', marginBottom: 8 }}>Lucas-Kanade</div>
                            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '0 0 10px', lineHeight: 1.45 }}>
                              Points saillants : rapide, adapté au suivi d’objets précis.
                            </p>
                            <div className="mono" style={{ fontSize: 13 }}>
                              Vitesse moy. :{' '}
                              <strong style={{ color: 'var(--cyan)' }}>
                                {comparison.lucas_kanade?.avg_fps != null ? `${comparison.lucas_kanade.avg_fps.toFixed(1)} img/s` : '—'}
                              </strong>
                            </div>
                            <div className="mono" style={{ fontSize: 13, marginTop: 6 }}>
                              Mouvement moy. :{' '}
                              <strong style={{ color: 'var(--cyan)' }}>
                                {comparison.lucas_kanade?.avg_magnitude != null ? comparison.lucas_kanade.avg_magnitude : '—'}
                              </strong>
                            </div>
                            {comparison.winner_speed === 'lucas_kanade' && (
                              <span className="badge badge-green" style={{ marginTop: 10, display: 'inline-block' }}>
                                Plus rapide sur ce résultat
                              </span>
                            )}
                          </div>
                          <div
                            style={{
                              padding: 14,
                              borderRadius: 10,
                              border: '1px solid var(--border)',
                              borderTop: '3px solid var(--orange)',
                            }}
                          >
                            <div style={{ fontWeight: 700, color: 'var(--orange)', marginBottom: 8 }}>Farneback</div>
                            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '0 0 10px', lineHeight: 1.45 }}>
                              Champ dense : voit le mouvement partout sur l’image, plus lourd à calculer.
                            </p>
                            <div className="mono" style={{ fontSize: 13 }}>
                              Vitesse moy. :{' '}
                              <strong style={{ color: 'var(--orange)' }}>
                                {comparison.farneback?.avg_fps != null ? `${comparison.farneback.avg_fps.toFixed(1)} img/s` : '—'}
                              </strong>
                            </div>
                            <div className="mono" style={{ fontSize: 13, marginTop: 6 }}>
                              Mouvement moy. :{' '}
                              <strong style={{ color: 'var(--orange)' }}>
                                {comparison.farneback?.avg_magnitude != null ? comparison.farneback.avg_magnitude : '—'}
                              </strong>
                            </div>
                            {comparison.winner_speed === 'farneback' && (
                              <span className="badge badge-green" style={{ marginTop: 10, display: 'inline-block' }}>
                                Plus rapide sur ce résultat
                              </span>
                            )}
                          </div>
                        </div>

                        <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.55 }}>
                          <strong>À retenir :</strong> Lucas-Kanade privilégie la vitesse et le suivi ciblé ; Farneback donne une vision complète du
                          mouvement sur toute l’image. Le graphique ci-dessous compare l’intensité du mouvement détecté par chaque méthode sur un
                          échantillon d’images.
                        </p>

                        {sample.length > 0 && (
                          <div style={{ height: 220 }}>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={sample} margin={{ top: 4, right: 8, left: -20, bottom: 4 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                <XAxis dataKey="frame" stroke="var(--text-muted)" tick={{ fontSize: 9 }} />
                                <YAxis stroke="var(--text-muted)" tick={{ fontSize: 9 }} />
                                <Tooltip content={<ChartTip />} />
                                <Legend wrapperStyle={{ fontSize: 11 }} />
                                <Line type="monotone" dataKey="lk_mag" name="Lucas-Kanade" stroke="var(--cyan)" dot={false} strokeWidth={1.5} />
                                <Line type="monotone" dataKey="fb_mag" name="Farneback" stroke="var(--orange)" dot={false} strokeWidth={1.5} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>

              <div className="card" style={{ padding: 18 }}>
                <div className="section-title" style={{ marginBottom: 4 }}>
                  Alertes
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 14px', lineHeight: 1.5 }}>
                  Événements sortant des seuils habituels.
                </p>
                {alerts.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)', fontSize: 14, margin: 0 }}>Aucune alerte.</p>
                ) : (
                  <div className="scroll-area" style={{ maxHeight: 280 }}>
                    {alerts.slice(0, 50).map((a, i) => (
                      <div key={i} className="alert-row">
                        <AlertTriangle size={14} color="var(--orange)" />
                        <span className="badge badge-orange">{alertLabel(a.alert_type)}</span>
                        <span style={{ flex: 1, fontSize: 13, color: 'var(--text-secondary)' }}>{a.description}</span>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {a.timestamp_sec != null ? `${Number(a.timestamp_sec).toFixed(1)} s` : a.frame_index != null ? `img ${a.frame_index}` : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {alerts.length > 50 && (
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12, marginBottom: 0 }}>
                    … et {alerts.length - 50} autre(s) — export sur la page Export.
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
