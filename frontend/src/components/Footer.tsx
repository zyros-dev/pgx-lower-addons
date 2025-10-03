import React from 'react';
import './Footer.css';

const Footer: React.FC = () => {
  return (
    <footer className="footer">
      <div className="footer-content">
        <div className="footer-links">
          <a href="http://localhost:8000/download/paper" target="_blank" rel="noopener noreferrer">
            Download Paper
          </a>
          <span className="separator">|</span>
          <a href="http://localhost:8000/download/slides" target="_blank" rel="noopener noreferrer">
            Download Slides
          </a>
          <span className="separator">|</span>
          <a href="https://github.com/zyros-dev" target="_blank" rel="noopener noreferrer">
            https://github.com/zyros-dev
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
