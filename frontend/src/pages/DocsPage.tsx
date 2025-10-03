import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/tokyo-night-light.css';
import './MarkdownPage.css';

const DocsPage: React.FC = () => {
  const [markdown, setMarkdown] = useState<string>('# Documentation\n\nLoading...');

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const response = await fetch('http://localhost:8000/content/README.md');
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
                src={`http://localhost:8000/content/${props.src}`}
                alt={props.alt || ''}
              />
            ),
          }}
        >
          {markdown}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default DocsPage;
