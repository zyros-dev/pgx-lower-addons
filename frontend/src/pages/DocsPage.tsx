import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import { API_BASE_URL } from '../config';
import BrandingFooter from '../components/BrandingFooter';
import 'highlight.js/styles/tokyo-night-light.css';
import './MarkdownPage.css';

const DocsPage: React.FC = () => {
  const [markdown, setMarkdown] = useState<string>('# Documentation\n\nLoading...');

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/content/README.md`);
        const text = await response.text();
        setMarkdown(text);
      } catch (error) {
        setMarkdown('# Error\n\nFailed to load documentation.');
      }
    };
    fetchDocs();
  }, []);

  return (
    <div className="markdown-page">
      <div className="markdown-content">
        <ReactMarkdown
          rehypePlugins={[rehypeHighlight]}
          components={{
            img: ({ node, ...props }) => (
              <img
                {...props}
                src={props.src?.startsWith('data:') || props.src?.startsWith('http') ? props.src : `${API_BASE_URL}/content/${props.src}`}
                alt={props.alt || ''}
              />
            ),
          }}
        >
          {markdown}
        </ReactMarkdown>
      </div>
      <BrandingFooter />
    </div>
  );
};

export default DocsPage;
