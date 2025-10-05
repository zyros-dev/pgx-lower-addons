import React from 'react';
import './BrandingFooter.css';

const BrandingFooter: React.FC = () => {
  return (
    <div className="branding-footer">
      <div className="branding-content">
        <img src="/logo512.png" alt="pgx-lower" className="branding-logo" />
      </div>
    </div>
  );
};

export default BrandingFooter;
