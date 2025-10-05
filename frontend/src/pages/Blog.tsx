import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import { API_BASE_URL } from '../config';
import 'highlight.js/styles/tokyo-night-light.css';
import './MarkdownPage.css';

const Blog: React.FC = () => {
  const [markdown, setMarkdown] = useState<string>('');

  useEffect(() => {
    const fetchMarkdown = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/content/blog.md`);
        const text = await response.text();
        setMarkdown(text);
      } catch (error) {
        console.error('Failed to fetch blog content:', error);
        setMarkdown('# Error\n\nFailed to load blog content.');
      }
    };

    fetchMarkdown();
  }, []);

  return (
    <div className="markdown-page">
      <div className="markdown-content">
        <ReactMarkdown
        remarkPlugins={[remarkGfm]}
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
    </div>
  );
};

export default Blog;
