// src/index.js
// Point d'entrée du frontend React.
// Monte l'application dans le DOM et charge les styles globaux.
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<React.StrictMode><App /></React.StrictMode>);
