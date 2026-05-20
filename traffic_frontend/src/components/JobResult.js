// src/components/JobResult.js
// Composant réutilisable affichant le résultat d'un job vidéo.
// Il présente des stats, un graphique de flux, les pistes et les alertes.
import React, { useState } from 'react';
import { CheckCircle, AlertTriangle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function JobResult({ result }) {
  const [tab, setTab] = useState('stats');
  if (!result) return null;

  const frames = result.frame_results || [];
  const sample = frames.filter((_, i) => i % Math.max(1, Math.floor(frames.length / 80)) === 0);

  return (
    <div className="card fade-in" style={{ overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <CheckCircle size={16} color="var(--green)" />
        <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>
          Analyse terminée
        </span>
        <span className="mono badge badge-cyan" style={{ marginLeft: 4 }}>Job {result.job_id}</span>
        <span className="badge badge-green" style={{ marginLeft: 'auto' }}>{result.method}</span>
      </div>

      {/* Tabs */}
      <div className="tab-bar" style={{ padding: '0 20px', borderBottom: '1px solid var(--border)' }}>
        {[['stats','Statistiques'],['flow','Flot'],['tracks','Tracks'],['alerts','Alertes']].map(([k, l]) => (
          <button key={k} className={`tab-btn ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>

      <div style={{ padding: 20 }}>
        {tab === 'stats' && (
          <>
            <div className="grid-2" style={{ gap: 10, marginBottom: 16 }}>
              {[
                ['Frames traitées', result.processed_frames,              'cyan'  ],
                ['FPS orig.',       result.fps_original,                  'purple'],
                ['FPS traitement',  result.avg_processing_fps?.toFixed(1),'green' ],
                ['Alertes',         result.stats?.total_alerts,           'red'   ],
                ['Tracks actifs',   result.stats?.tracking?.active_tracks,'cyan'  ],
                ['Véhicules rap.', result.stats?.tracking?.fast_vehicles, 'orange'],
              ].map(([k, v, c]) => (
                <div key={k} className="stat-card" style={{ padding: '12px 14px' }}>
                  <span className="stat-label">{k}</span>
                  <div className="stat-value" style={{ fontSize: 20, color: `var(--${c})` }}>{v ?? '—'}</div>
                </div>
              ))}
            </div>

            <div className="grid-2" style={{ gap: 10 }}>
              {result.stats?.lk_avg_fps && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>LK FPS moyen</span>
                  <span className="mono" style={{ color: 'var(--cyan)' }}>{result.stats.lk_avg_fps}</span>
                </div>
              )}
              {result.stats?.fb_avg_fps && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>FB FPS moyen</span>
                  <span className="mono" style={{ color: 'var(--orange)' }}>{result.stats.fb_avg_fps}</span>
                </div>
              )}
            </div>
          </>
        )}

        {tab === 'flow' && sample.length > 0 && (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={sample}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="frame_index" stroke="var(--text-muted)" tick={{ fontSize: 9, fontFamily: 'var(--font-mono)' }} />
              <YAxis stroke="var(--text-muted)" tick={{ fontSize: 9, fontFamily: 'var(--font-mono)' }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11, fontFamily: 'var(--font-mono)' }}
              />
              <Line type="monotone" dataKey="lk_avg_magnitude" name="LK" stroke="var(--cyan)" dot={false} strokeWidth={1.5} />
              <Line type="monotone" dataKey="fb_avg_magnitude" name="FB" stroke="var(--orange)" dot={false} strokeWidth={1.5} />
            </LineChart>
          </ResponsiveContainer>
        )}

        {tab === 'tracks' && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr><th>ID</th><th>Vitesse (px/f)</th><th>Direction</th><th>Statut</th></tr>
              </thead>
              <tbody>
                {(result.tracks || []).slice(0, 30).map(t => (
                  <tr key={t.track_id}>
                    <td><span className="mono" style={{ color: 'var(--cyan)' }}>#{t.track_id}</span></td>
                    <td><span className="mono">{t.speed_pixels_per_frame}</span></td>
                    <td><span className="mono">{t.direction_angle_deg}°</span></td>
                    <td>{t.is_fast
                      ? <span className="badge badge-red">Rapide</span>
                      : <span className="badge badge-green">Normal</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'alerts' && (
          <div className="scroll-area">
            {(result.alerts || []).length === 0
              ? <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 30, fontSize: 13 }}>Aucune alerte</div>
              : (result.alerts || []).map((a, i) => (
                <div key={i} className="alert-row">
                  <AlertTriangle size={13} color="var(--orange)" />
                  <span className="badge badge-orange">{a.alert_type}</span>
                  <span style={{ flex: 1, fontSize: 12, color: 'var(--text-secondary)' }}>{a.description}</span>
                  <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>f{a.frame_index}</span>
                </div>
              ))
            }
          </div>
        )}
      </div>
    </div>
  );
}
