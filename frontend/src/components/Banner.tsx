import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './Banner.css';

const Banner: React.FC = () => {
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    const fetchVersion = async () => {
      try {
        const response = await fetch('http://localhost:8000/version');
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
          {/* Logo placeholder - will be replaced */}
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
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
