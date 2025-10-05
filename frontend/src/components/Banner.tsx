import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE_URL } from '../config';
import './Banner.css';

const Banner: React.FC = () => {
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    const fetchVersion = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/version`);
        const data = await response.json();
        setVersion(data.version);
      } catch (error) {
        console.error('Failed to fetch version:', error);
      }
    };
    fetchVersion();
  }, []);

  return (
    <nav className="banner">
      <div className="banner-content">
        <div className="banner-logo">
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <img src="/logo192.png" alt="pgx-lower logo" className="banner-icon" />
            <h1>pgx-lower {version && <span className="version">v{version}</span>}</h1>
          </Link>
        </div>
        <div className="banner-links">
          <Link to="/">About</Link>
          <Link to="/blog">Blog</Link>
          <Link to="/query">Query</Link>
        </div>
      </div>
    </nav>
  );
};

export default Banner;
