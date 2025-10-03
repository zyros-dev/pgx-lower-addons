import React, { useState } from 'react';
import Editor, { loader } from '@monaco-editor/react';
import githubLight from 'monaco-themes/themes/GitHub.json';
import './QueryPage.css';

interface Output {
  title: string;
  content: string;
  latency_ms?: number;
}

interface DatabaseResult {
  database: string;
  version: string;
  latency_ms: number;
  outputs: Output[];
}

interface QueryResult {
  main_display: string;
  results: DatabaseResult[];
}

const QueryPage: React.FC = () => {
  const [query, setQuery] = useState<string>('-- Select a TPC-H query or write your own');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [expandedDatabases, setExpandedDatabases] = useState<Set<string>>(new Set());
  const [editorHeight, setEditorHeight] = useState<number>(250);
  const [mainDisplayHeight, setMainDisplayHeight] = useState<number>(100);
  const [outputHeights, setOutputHeights] = useState<{[key: string]: number}>({});

  const handleEditorWillMount = (monaco: any) => {
    monaco.editor.defineTheme('github-light', githubLight);
  };

  const createResizeHandler = (setHeight: (h: number) => void, currentHeight: number, minHeight: number = 100) => {
    return (e: React.MouseEvent) => {
      const startY = e.clientY;
      const startHeight = currentHeight;

      const handleMouseMove = (e: MouseEvent) => {
        const delta = e.clientY - startY;
        setHeight(Math.max(minHeight, startHeight + delta));
      };

      const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    };
  };

  const loadQuery = async (queryNumber: number) => {
    try {
      const response = await fetch(`http://localhost:8000/resources/${queryNumber}.sql`);
      const sql = await response.text();
      setQuery(sql);
    } catch (error) {
      console.error('Failed to load query:', error);
    }
  };

  const executeQuery = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      setResult(data.result);
    } catch (error) {
      console.error('Failed to execute query:', error);
    }
    setLoading(false);
  };

  const toggleDatabase = (dbName: string) => {
    const newExpanded = new Set(expandedDatabases);
    if (newExpanded.has(dbName)) {
      newExpanded.delete(dbName);
    } else {
      newExpanded.add(dbName);
    }
    setExpandedDatabases(newExpanded);
  };

  return (
    <div className="query-page">
      {/* Performance Dashboard Placeholder */}
      <div className="performance-dashboard-section">
        <h3>Performance Dashboard</h3>
        <p className="placeholder-text">Coming soon...</p>
      </div>

      {/* SQL Editor */}
      <div className="editor-section">
        <h3>SQL Query</h3>

        {/* TPC-H Query Buttons */}
        <div className="tpch-buttons-container">
          <span className="tpch-label">TPC-H Queries:</span>
          <div className="tpch-buttons">
            {Array.from({ length: 22 }, (_, i) => i + 1).map((num) => (
              <button
                key={num}
                className="tpch-btn"
                onClick={() => loadQuery(num)}
              >
                Q{num}
              </button>
            ))}
          </div>
        </div>

        <div className="monaco-editor-container">
          <div className="monaco-editor-wrapper" style={{ minHeight: '150px', height: `${editorHeight}px` }}>
            <Editor
              height="100%"
              defaultLanguage="sql"
              theme="github-light"
              value={query}
              onChange={(value) => setQuery(value || '')}
              beforeMount={handleEditorWillMount}
              options={{
                minimap: { enabled: false },
                fontSize: 15,
                automaticLayout: true,
              }}
            />
          </div>
          <div
            className="resize-handle"
            onMouseDown={createResizeHandler(setEditorHeight, editorHeight, 150)}
          />
        </div>
        <div className="editor-actions">
          <button className="execute-btn" onClick={executeQuery} disabled={loading}>
            {loading ? 'Executing...' : 'Execute Query'}
          </button>
          <span className="resize-hint">Click and drag the bottom of the editor to resize!</span>
        </div>
      </div>

      {/* Main Display */}
      {result && (
        <>
          <div className="main-display-section">
            <h3>Output</h3>
            <div className="resizable-textarea-container">
              <textarea
                className="main-display-box"
                value={result.main_display}
                readOnly
                style={{ height: `${mainDisplayHeight}px` }}
              />
              <div
                className="resize-handle"
                onMouseDown={createResizeHandler(setMainDisplayHeight, mainDisplayHeight)}
              />
            </div>
          </div>

          {/* Database Results */}
          <div className="database-results-section">
            {result.results.map((dbResult, idx) => (
              <div key={idx} className="database-result">
                <div
                  className="database-header"
                  onClick={() => toggleDatabase(dbResult.database)}
                >
                  <div>
                    <span className="database-name">{dbResult.database} | {dbResult.version}</span>
                  </div>
                  <div>
                    <span className="database-latency">{dbResult.latency_ms}ms</span>
                    <span className="collapse-icon">
                      {expandedDatabases.has(dbResult.database) ? '▼' : '▶'}
                    </span>
                  </div>
                </div>
                {expandedDatabases.has(dbResult.database) && (
                  <div className="database-outputs">
                    {dbResult.outputs.map((output, outIdx) => {
                      const outputKey = `${dbResult.database}-${outIdx}`;
                      const outputHeight = outputHeights[outputKey] || 120;

                      return (
                        <div key={outIdx} className="output-block">
                          <div className="output-header">
                            <span className="output-title">{output.title}</span>
                            {output.latency_ms && (
                              <span className="output-latency">{output.latency_ms}ms</span>
                            )}
                          </div>
                          <div className="resizable-textarea-container">
                            <textarea
                              className="output-content"
                              value={output.content}
                              readOnly
                              style={{ height: `${outputHeight}px` }}
                            />
                            <div
                              className="resize-handle"
                              onMouseDown={createResizeHandler(
                                (h) => setOutputHeights({...outputHeights, [outputKey]: h}),
                                outputHeight
                              )}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default QueryPage;
