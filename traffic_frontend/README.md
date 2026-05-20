# 🚗 TrafficVision — Frontend

Interface React complète pour le backend Traffic Analysis API.

## ⚡ Démarrage rapide

### Prérequis
- Node.js 18+ (https://nodejs.org)
- Backend FastAPI démarré sur `http://localhost:8000`

### Installation & lancement

```bash
# 1. Installer les dépendances
npm install

# 2. Lancer en développement
npm start

# 3. Ouvrir dans le navigateur
# http://localhost:3000
```

### Build production

```bash
npm run build
# Les fichiers sont dans /build
```

## 📁 Structure

```
src/
├── App.js              # Router + Layout + Sidebar
├── App.css             # Layout, sidebar, topbar
├── index.css           # Design system (variables, boutons, cards...)
├── pages.css           # Composants pages (dropzone, tabs, pipeline...)
├── index.js            # Entry point
│
├── pages/
│   ├── Dashboard.js    # Vue d'ensemble + stats
│   ├── VideoProcess.js # Upload + traitement vidéo
│   ├── CameraPage.js   # Webcam live stream
│   ├── FlowAnalysis.js # Test flot sur 2 images + benchmark
│   ├── ResultsPage.js  # Charts, tracks, alertes, comparaison
│   └── ExportPage.js   # Téléchargements JSON/CSV/vidéo
│
├── components/
│   └── JobResult.js    # Résultat inline après traitement
│
└── services/
    └── api.js          # Toutes les fonctions API (axios)
```

## 🌐 Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Vue générale, statut API, pipeline |
| Vidéo | `/video` | Upload + traitement avec paramètres |
| Caméra | `/camera` | Stream live MJPEG, snapshot, batch |
| Flot Optique | `/flow` | Test LK/Farneback sur images, benchmark |
| Résultats | `/results` | Charts recharts, tracks, alertes |
| Export | `/export` | JSON, CSV (tracks/alertes/frames), vidéo |

## ⚙️ Configuration

Créez un fichier `.env` à la racine :

```env
REACT_APP_API_URL=http://localhost:8000
```

Par défaut le proxy dans `package.json` redirige vers `localhost:8000`.
