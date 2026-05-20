// src/pages/Dashboard.js
// Page d'accueil du frontend.
// Elle affiche l'état de l'API, le nombre de jobs et les liens vers les modules.
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity, Upload, Camera, BarChart2, Download,
  CheckCircle, Clock, AlertTriangle, Cpu, ArrowRight, Play
} from 'lucide-react';
import { healthCheck, listJobs } from '../services/api';

const FEATURES = [
  { icon: Upload,   color: 'cyan',   title: 'Upload Vidéo',   desc: 'Chargez un fichier MP4/AVI pour analyse complète',    path: '/video'   },
  { icon: Camera,   color: 'green',  title: 'Caméra Live',    desc: 'Flux webcam en temps réel avec overlay optique',      path: '/camera'  },
  { icon: BarChart2, color: 'purple', title: 'Résultats',      desc: 'Analyse comparative des méthodes et des trajectoires', path: '/results' },
  { icon: Download, color: 'cyan',   title: 'Export',         desc: 'JSON, CSV, vidéo annotée téléchargeables',            path: '/export'  },
];

const PIPELINE = [
  { step: '01', label: 'Upload',         desc: 'Chargez votre vidéo de trafic' },
  { step: '02', label: 'Paramétrage',    desc: 'Choisissez la méthode et les seuils' },
  { step: '03', label: 'Traitement',     desc: 'Pipeline Lucas-Kanade + Farneback' },
  { step: '04', label: 'Visualisation',  desc: 'Trajectoires, vitesses, alertes' },
  { step: '05', label: 'Export',         desc: 'Téléchargez les résultats' },
];

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      healthCheck().then(r => setHealth(r.data)).catch(() => setHealth(null)),
      listJobs().then(r => setJobs(r.data)).catch(() => setJobs([])),
    ]).finally(() => setLoading(false));
  }, []);

  // Comptage rapide des différents états de jobs.
  const done  = jobs.filter(j => j.status === 'done').length;
  const proc  = jobs.filter(j => j.status === 'processing').length;
  const err   = jobs.filter(j => j.status === 'error').length;

  return (
    <div className="fade-in">
      {/* Hero */}
      <div className="dashboard-hero card scan-overlay" style={{ marginBottom: 28, padding: '32px 36px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 20 }}>
          <div>
            <div className="badge badge-cyan" style={{ marginBottom: 14 }}>
              <Activity size={10} /> Système actif
            </div>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 36, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1, marginBottom: 12 }}>
              Analyse du<br />
              <span style={{ color: 'var(--cyan)' }}>mouvement de trafic</span>
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14, maxWidth: 460, lineHeight: 1.6 }}>
              Plateforme avancée utilisant <strong style={{ color: 'var(--text-primary)' }}>Lucas–Kanade</strong> et{' '}
              <strong style={{ color: 'var(--text-primary)' }}>Farneback</strong> pour détecter, tracker et analyser
              les véhicules en temps réel.
            </p>
            <div style={{ display: 'flex', gap: 12, marginTop: 22, flexWrap: 'wrap' }}>
              <Link to="/video" className="btn btn-primary btn-lg">
                <Play size={16} /> Analyser une vidéo
              </Link>
              <Link to="/camera" className="btn btn-ghost btn-lg">
                <Camera size={16} /> Démo caméra live
              </Link>
            </div>
          </div>
          <div className="dashboard-hero-grid">
            {['Lucas–Kanade', 'Farneback', 'Tracking', 'Alertes'].map((m, i) => (
              <div key={m} className="hero-method-badge" style={{ animationDelay: `${i * 0.1}s` }}>
                <Cpu size={12} />
                {m}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid-4" style={{ marginBottom: 28 }}>
        {[
          { label: 'Jobs totaux',  value: jobs.length, icon: Activity,      color: 'cyan'   },
          { label: 'Terminés',     value: done,         icon: CheckCircle,   color: 'green'  },
          { label: 'En cours',     value: proc,         icon: Clock,         color: 'orange' },
          { label: 'Erreurs',      value: err,          icon: AlertTriangle, color: 'red'    },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="stat-label">{s.label}</span>
              <s.icon size={15} color={`var(--${s.color})`} />
            </div>
            <div className={`stat-value`} style={{ color: `var(--${s.color})` }}>
              {loading ? '—' : s.value}
            </div>
          </div>
        ))}
      </div>

 

      {/* Features */}
      <div className="section-title">Modules</div>
      <div className="grid-auto" style={{ marginBottom: 28 }}>
        {FEATURES.map(({ icon: Icon, color, title, desc, path }) => (
          <Link key={path} to={path} style={{ textDecoration: 'none' }}>
            <div className="card feature-card" style={{ padding: 20, height: '100%', cursor: 'pointer' }}>
              <div className={`feature-icon bg-${color}`}>
                <Icon size={18} color={`var(--${color})`} />
              </div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 14, marginBottom: 6, marginTop: 14 }}>
                {title}
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.5 }}>{desc}</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 14, color: `var(--${color})`, fontSize: 12, fontWeight: 600 }}>
                Accéder <ArrowRight size={12} />
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Pipeline */}
      <div className="section-title">Pipeline de traitement</div>
      <div className="card" style={{ padding: '20px 24px' }}>
        <div className="pipeline-steps">
          {PIPELINE.map((s, i) => (
            <div key={s.step} className="pipeline-step">
              <div className="pipeline-num">{s.step}</div>
              {i < PIPELINE.length - 1 && <div className="pipeline-line" />}
              <div className="pipeline-label">{s.label}</div>
              <div className="pipeline-desc">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
