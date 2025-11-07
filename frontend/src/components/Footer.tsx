import React from 'react';
import { API_BASE_URL } from '../config';
import './Footer.css';

const Footer: React.FC = () => {
  return (
    <footer className="footer">
      <div className="footer-content">
        <div className="footer-links">
          <a href={`${API_BASE_URL}/download/Thesis_B_Anonymous.pdf`} target="_blank" rel="noopener noreferrer">
            Download Slides B
          </a>
          <span className="separator">|</span>
          <a href={`${API_BASE_URL}/download/Thesis_C_Anonymous.pdf`} target="_blank" rel="noopener noreferrer">
            Download Slides C
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
