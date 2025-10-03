import React from 'react';
import { Link } from 'react-router-dom';
import './Banner.css';

const Banner: React.FC = () => {
  return (
    <nav className="banner">
      <div className="banner-content">
        <div className="banner-logo">
          {/* Logo placeholder - will be replaced */}
          <h1>pgx-lower</h1>
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
