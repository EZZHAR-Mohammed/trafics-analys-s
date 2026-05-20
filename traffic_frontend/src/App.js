// src/App.js
// Composant principal du frontend React.
// Il installe le router, le menu de navigation et vérifie le statut de l'API.
import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import {
  Activity, Upload, Camera, BarChart2,
  Bell, Download, Cpu, Radio, ChevronRight, Wifi, WifiOff
} from 'lucide-react';
import { healthCheck } from './services/api';

import Dashboard      from './pages/Dashboard';
import VideoProcess   from './pages/VideoProcess';
import CameraPage     from './pages/CameraPage';
import ResultsPage    from './pages/ResultsPage';
import ExportPage     from './pages/ExportPage';

import './index.css';
import './pages.css';
import './App.css';

const NAV_ITEMS = [
  { path: '/',          icon: Activity,  label: 'Dashboard'   },
  { path: '/video',     icon: Upload,    label: 'Vidéo'       },
  { path: '/camera',    icon: Camera,    label: 'Caméra Live' },
  { path: '/results',   icon: BarChart2, label: 'Résultats'   },
  { path: '/export',    icon: Download,  label: 'Export'      },
];

function Sidebar({ apiOnline }) {
  const location = useLocation();
  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="logo-icon">
          <Radio size={20} color="var(--cyan)" />
        </div>
        <div>
          <div className="logo-title">TrafficVision</div>
          <div className="logo-sub">Analyse de trafic</div>
        </div>
      </div>

      {/* API Status */}
      <div className={`api-status ${apiOnline ? 'online' : 'offline'}`}>
        {apiOnline ? <Wifi size={13} /> : <WifiOff size={13} />}
        <span>API {apiOnline ? 'connectée' : 'hors ligne'}</span>
        <div className={`dot-status ${apiOnline ? 'dot-green' : 'dot-red'}`} />
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {NAV_ITEMS.map(({ path, icon: Icon, label }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon size={16} />
            <span>{label}</span>
            <ChevronRight size={13} className="nav-chevron" />
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-label">
          <Cpu size={12} />
          OpenCV + FastAPI backend
        </div>
        <div className="sidebar-footer-sub">Lucas-Kanade · Farneback</div>
      </div>
    </aside>
  );
}

function Layout({ apiOnline }) {
  const location = useLocation();
  const current = NAV_ITEMS.find(n => n.path === location.pathname) || NAV_ITEMS[0];

  return (
    <div className="app-layout">
      <Sidebar apiOnline={apiOnline} />
      <div className="main-wrapper">
        <header className="topbar">
          <div className="topbar-left">
            <span className="topbar-page">{current.label}</span>
          </div>
          <div className="topbar-right">
            <span className="topbar-version badge badge-cyan"></span>
          </div>
        </header>
        <main className="main-content">
          <Routes>
            <Route path="/"        element={<Dashboard />} />
            <Route path="/video"   element={<VideoProcess />} />
            <Route path="/camera"  element={<CameraPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/export"  element={<ExportPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const [apiOnline, setApiOnline] = useState(false);

  useEffect(() => {
    // Vérifie périodiquement que le backend est accessible.
    const check = async () => {
      try { await healthCheck(); setApiOnline(true); }
      catch { setApiOnline(false); }
    };
    check();
    const t = setInterval(check, 10000);
    return () => clearInterval(t);
  }, []);

  return (
    <BrowserRouter>
      <Layout apiOnline={apiOnline} />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-body)',
            fontSize: '13px',
          },
          success: { iconTheme: { primary: 'var(--green)', secondary: '#000' } },
          error:   { iconTheme: { primary: 'var(--red)',   secondary: '#000' } },
        }}
      />
    </BrowserRouter>
  );
}
