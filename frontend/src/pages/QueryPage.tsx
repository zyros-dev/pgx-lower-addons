import React, { useState, useEffect } from 'react';
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
  cached: boolean;
  outputs: Output[];
}

interface QueryResult {
  main_display: string;
  results: DatabaseResult[];
}

interface PerformanceStat {
  database: string;
  hour_bucket: string;
  query_count: number;
  unique_queries: number;
  min_latency_ms: number;
  p25_latency_ms: number;
  p50_latency_ms: number;
  p75_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  max_latency_ms: number;
  mean_latency_ms: number;
}

const QueryPage: React.FC = () => {
  const [query, setQuery] = useState<string>('-- Select a TPC-H query or write your own');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [isCached, setIsCached] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [expandedDatabases, setExpandedDatabases] = useState<Set<string>>(new Set());
  const [editorHeight, setEditorHeight] = useState<number>(250);
  const [mainDisplayHeight, setMainDisplayHeight] = useState<number>(100);
  const [outputHeights, setOutputHeights] = useState<{[key: string]: number}>({});
  const [performanceStats, setPerformanceStats] = useState<PerformanceStat[]>([]);
  const [performanceDashboardExpanded, setPerformanceDashboardExpanded] = useState<boolean>(true);

  // Calculate height based on content, max 100 lines, +3 rows for padding
  const calculateHeight = (content: string, lineHeight: number = 20) => {
    const lines = content.split('\n').length;
    const maxLines = 100;
    const actualLines = Math.min(lines + 3, maxLines);
    return actualLines * lineHeight;
  };

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
      setIsCached(data.cached || false);
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

  const fetchPerformanceStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/stats/performance?limit=24');
      const data = await response.json();
      setPerformanceStats(data.stats);
    } catch (error) {
      console.error('Failed to fetch performance stats:', error);
    }
  };

  useEffect(() => {
    fetchPerformanceStats();
    const interval = setInterval(fetchPerformanceStats, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const renderPerformanceChart = (stats: PerformanceStat[]) => {
    if (stats.length === 0) return null;

    // Group by database
    const statsByDatabase = stats.reduce((acc, stat) => {
      if (!acc[stat.database]) acc[stat.database] = [];
      acc[stat.database].push(stat);
      return acc;
    }, {} as Record<string, PerformanceStat[]>);

    return Object.entries(statsByDatabase).map(([database, dbStats]) => {
      const latestStat = dbStats[0]; // Most recent stats

      return (
        <div key={database} className="performance-chart">
          <h4>{database.toUpperCase()} Performance</h4>
          <div className="stats-summary">
            <div className="stat-item">
              <span className="stat-label">Total Queries</span>
              <span className="stat-value">{latestStat.query_count}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Unique Queries</span>
              <span className="stat-value">{latestStat.unique_queries}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Mean Latency</span>
              <span className="stat-value">{latestStat.mean_latency_ms.toFixed(2)}ms</span>
            </div>
          </div>

          <div className="percentile-chart">
            <div className="chart-bar-container">
              <div className="chart-label">Min</div>
              <div className="chart-bar-wrapper">
                <div
                  className="chart-bar chart-bar-min"
                  style={{ width: `${Math.max((latestStat.min_latency_ms / latestStat.max_latency_ms) * 100, 5)}%` }}
                >
                  <span className="chart-value">{latestStat.min_latency_ms.toFixed(2)}ms</span>
                </div>
              </div>
            </div>

            <div className="chart-bar-container">
              <div className="chart-label">p25</div>
              <div className="chart-bar-wrapper">
                <div
                  className="chart-bar chart-bar-p25"
                  style={{ width: `${Math.max((latestStat.p25_latency_ms / latestStat.max_latency_ms) * 100, 5)}%` }}
                >
                  <span className="chart-value">{latestStat.p25_latency_ms.toFixed(2)}ms</span>
                </div>
              </div>
            </div>

            <div className="chart-bar-container">
              <div className="chart-label">p50</div>
              <div className="chart-bar-wrapper">
                <div
                  className="chart-bar chart-bar-p50"
                  style={{ width: `${Math.max((latestStat.p50_latency_ms / latestStat.max_latency_ms) * 100, 5)}%` }}
                >
                  <span className="chart-value">{latestStat.p50_latency_ms.toFixed(2)}ms</span>
                </div>
              </div>
            </div>

            <div className="chart-bar-container">
              <div className="chart-label">p75</div>
              <div className="chart-bar-wrapper">
                <div
                  className="chart-bar chart-bar-p75"
                  style={{ width: `${Math.max((latestStat.p75_latency_ms / latestStat.max_latency_ms) * 100, 5)}%` }}
                >
                  <span className="chart-value">{latestStat.p75_latency_ms.toFixed(2)}ms</span>
                </div>
              </div>
            </div>

            <div className="chart-bar-container">
              <div className="chart-label">p95</div>
              <div className="chart-bar-wrapper">
                <div
                  className="chart-bar chart-bar-p95"
                  style={{ width: `${Math.max((latestStat.p95_latency_ms / latestStat.max_latency_ms) * 100, 5)}%` }}
                >
                  <span className="chart-value">{latestStat.p95_latency_ms.toFixed(2)}ms</span>
                </div>
              </div>
            </div>

            <div className="chart-bar-container">
              <div className="chart-label">p99</div>
              <div className="chart-bar-wrapper">
                <div
                  className="chart-bar chart-bar-p99"
                  style={{ width: `${Math.max((latestStat.p99_latency_ms / latestStat.max_latency_ms) * 100, 5)}%` }}
                >
                  <span className="chart-value">{latestStat.p99_latency_ms.toFixed(2)}ms</span>
                </div>
              </div>
            </div>

            <div className="chart-bar-container">
              <div className="chart-label">Max</div>
              <div className="chart-bar-wrapper">
                <div
                  className="chart-bar chart-bar-max"
                  style={{ width: '100%' }}
                >
                  <span className="chart-value">{latestStat.max_latency_ms.toFixed(2)}ms</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    });
  };

  return (
    <div className="query-page">
      {/* Performance Dashboard */}
      <div className="performance-dashboard-section">
        <div
          className="performance-dashboard-header"
          onClick={() => setPerformanceDashboardExpanded(!performanceDashboardExpanded)}
        >
          <h3>Performance Dashboard</h3>
          <span className="collapse-icon">
            {performanceDashboardExpanded ? '▼' : '▶'}
          </span>
        </div>
        {performanceDashboardExpanded && (
          <>
            {performanceStats.length > 0 ? (
              <div className="performance-charts">
                {renderPerformanceChart(performanceStats)}
              </div>
            ) : (
              <p className="placeholder-text">No performance data available yet. Run some queries to see statistics.</p>
            )}
          </>
        )}
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
                fontFamily: "'Source Code Pro', 'Courier New', monospace",
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
            <div className="output-section-header">
              <h3>Output</h3>
              {isCached && <span className="cached-badge">CACHED</span>}
            </div>
            <div className="resizable-textarea-container">
              <textarea
                className="main-display-box"
                value={result.main_display}
                readOnly
                wrap="off"
                style={{ height: `${mainDisplayHeight || calculateHeight(result.main_display)}px` }}
              />
              <div
                className="resize-handle"
                onMouseDown={createResizeHandler(setMainDisplayHeight, mainDisplayHeight || calculateHeight(result.main_display))}
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
                    {dbResult.cached && (
                      <span className="cached-badge">CACHED</span>
                    )}
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
                      const defaultHeight = calculateHeight(output.content);
                      const outputHeight = outputHeights[outputKey] || defaultHeight;

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
                              wrap="off"
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
