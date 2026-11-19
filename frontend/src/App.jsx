import React, { useState, useEffect } from 'react';
import {
  Search,
  MapPin,
  Briefcase,
  DollarSign,
  ExternalLink,
  Sparkles,
  Zap,
  Brain,
  SlidersHorizontal,
  TrendingUp,
  Clock,
  Building2,
  Layers,
  HelpCircle,
  Hash,
  ShieldCheck,
} from 'lucide-react';

const SAMPLE_QUERIES = [
  "Fresher looking for backend internships in Bangalore involving Python & FastAPI",
  "Deep learning neural networks and transformer architectures",
  "Full stack engineer React and Node.js with remote flexibility",
  "Data Engineer Apache Spark and Airflow ETL pipelines",
  "DevOps Engineer Kubernetes AWS Terraform",
];

const COMPANY_COLORS = {
  Elip: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  Razorpay: 'linear-gradient(135deg, #0284c7, #2563eb)',
  Postman: 'linear-gradient(135deg, #f97316, #ea580c)',
  Swiggy: 'linear-gradient(135deg, #fb923c, #ea580c)',
  Flipkart: 'linear-gradient(135deg, #2563eb, #eab308)',
  Zerodha: 'linear-gradient(135deg, #0284c7, #38bdf8)',
  CRED: 'linear-gradient(135deg, #18181b, #3f3f46)',
  Hasura: 'linear-gradient(135deg, #0284c7, #06b6d4)',
  BrowserStack: 'linear-gradient(135deg, #059669, #10b981)',
  'Ola Krutrim': 'linear-gradient(135deg, #dc2626, #b91c1c)',
};

export default function App() {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [experience, setExperience] = useState('');
  const [employmentType, setEmploymentType] = useState('');
  const [mode, setMode] = useState('hybrid'); // 'hybrid', 'bm25', 'vector'
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [executionTime, setExecutionTime] = useState(null);
  const [health, setHealth] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Load backend health and perform default search
  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => setHealth({ status: 'offline', total_jobs_indexed: 0 }));

    handleSearch(SAMPLE_QUERIES[0], 'hybrid');
  }, []);

  const handleSearch = async (overrideQuery = null, overrideMode = null) => {
    const q = overrideQuery !== null ? overrideQuery : query;
    const targetMode = overrideMode !== null ? overrideMode : mode;

    if (!q.trim()) return;

    if (overrideQuery !== null) {
      setQuery(overrideQuery);
    }
    if (overrideMode !== null) {
      setMode(overrideMode);
    }

    setLoading(true);
    setHasSearched(true);

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          location: location || null,
          experience: experience || null,
          employment_type: employmentType || null,
          mode: targetMode,
          top_k: 10,
        }),
      });

      const data = await response.json();
      setResults(data.results || []);
      setExecutionTime(data.execution_time_ms);
    } catch (err) {
      console.error('Search failed:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    handleSearch(null, newMode);
  };

  return (
    <div className="container">
      {/* Top Header */}
      <header className="header">
        <div className="brand-wrapper">
          <div className="brand-logo-icon">
            <Sparkles size={24} />
          </div>
          <div>
            <h1 className="brand-title">JobSearch AI</h1>
            <p className="brand-subtitle">
              Interactive Retrieval Comparison • Okapi BM25 vs. pgvector Semantic vs. Reciprocal Rank Fusion
            </p>
          </div>
        </div>

        <div>
          {health && (
            <div className="status-pill">
              <span className="status-ping">
                <span className="status-ping-dot"></span>
              </span>
              {health.status === 'healthy' ? (
                <span>PostgreSQL + pgvector ({health.total_jobs_indexed} jobs)</span>
              ) : (
                <span>Backend Offline</span>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Main Search Panel */}
      <div className="search-card">
        <div className="search-input-wrapper">
          <Search className="search-icon" size={22} />
          <input
            type="text"
            className="search-input"
            placeholder="Type your search intent (e.g. 'fresher backend developer in Bangalore involving Python & FastAPI')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="search-btn" onClick={() => handleSearch()} disabled={loading}>
            {loading ? 'Searching...' : (
              <>
                <span>Search</span>
                <Sparkles size={16} />
              </>
            )}
          </button>
        </div>

        {/* Quick Sample Queries */}
        <div className="sample-queries">
          <span className="sample-label">
            <TrendingUp size={14} /> Try:
          </span>
          {SAMPLE_QUERIES.map((sq, i) => (
            <button
              key={i}
              className="query-chip"
              onClick={() => handleSearch(sq)}
            >
              {sq.length > 55 ? sq.substring(0, 52) + '...' : sq}
            </button>
          ))}
        </div>

        {/* Structured Metadata Filters */}
        <div className="filters-row">
          <div className="filter-group">
            <label className="filter-label">Location Constraint</label>
            <select
              className="filter-select"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            >
              <option value="">All Locations</option>
              <option value="Bangalore">Bangalore</option>
              <option value="Hyderabad">Hyderabad</option>
              <option value="Pune">Pune</option>
              <option value="Remote">Remote</option>
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Experience Bracket</label>
            <select
              className="filter-select"
              value={experience}
              onChange={(e) => setExperience(e.target.value)}
            >
              <option value="">All Experience</option>
              <option value="Fresher">Fresher / Intern (0 yrs)</option>
              <option value="1-3 years">1–3 years</option>
              <option value="3-5 years">3–5 years</option>
              <option value="5+ years">5+ years (Senior / Staff)</option>
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Employment Type</label>
            <select
              className="filter-select"
              value={employmentType}
              onChange={(e) => setEmploymentType(e.target.value)}
            >
              <option value="">All Employment Types</option>
              <option value="Full-time">Full-time Position</option>
              <option value="Internship">Internship</option>
            </select>
          </div>
        </div>
      </div>

      {/* ─── RETRIEVAL MODE TABS ─── */}
      <div className="mode-navigation">
        <div className="mode-tabs-wrapper">
          <button
            className={`mode-tab ${mode === 'hybrid' ? 'mode-tab-active' : ''}`}
            onClick={() => handleModeChange('hybrid')}
          >
            <Layers size={17} />
            <span>Hybrid Search (RRF)</span>
            <span className="mode-badge badge-hybrid">Recommended</span>
          </button>

          <button
            className={`mode-tab ${mode === 'bm25' ? 'mode-tab-active mode-bm25' : ''}`}
            onClick={() => handleModeChange('bm25')}
          >
            <Zap size={17} />
            <span>BM25 Keywords</span>
            <span className="mode-badge badge-bm25">Exact Words</span>
          </button>

          <button
            className={`mode-tab ${mode === 'vector' ? 'mode-tab-active mode-vector' : ''}`}
            onClick={() => handleModeChange('vector')}
          >
            <Brain size={17} />
            <span>Vector Semantic</span>
            <span className="mode-badge badge-vector">pgvector HNSW</span>
          </button>
        </div>

        <div className="mode-description-banner">
          <HelpCircle size={14} />
          {mode === 'hybrid' && (
            <span>
              <strong>Hybrid RRF Mode:</strong> Merges both BM25 keywords and pgvector neural embeddings using Reciprocal Rank Fusion. Highest precision & recall.
            </span>
          )}
          {mode === 'bm25' && (
            <span>
              <strong>BM25 Keyword Mode:</strong> Pure tokenization & inverted index term frequencies. Great for exact keywords, misses conceptual matches.
            </span>
          )}
          {mode === 'vector' && (
            <span>
              <strong>Vector Semantic Mode:</strong> 384-dimensional dense transformer coordinates in PostgreSQL HNSW. Great for conceptual intent, may blur exact keywords.
            </span>
          )}
        </div>
      </div>

      {/* Results Meta Info */}
      {hasSearched && (
        <div className="results-meta">
          <div className="results-count">
            {loading ? (
              'Retrieving and ranking jobs...'
            ) : (
              <span>
                Showing <strong>{results.length}</strong> jobs via <strong>{mode.toUpperCase()}</strong> retrieval
              </span>
            )}
          </div>
          {executionTime !== null && (
            <div className="results-time">
              <Clock size={13} />
              <span>Query processed in <strong>{executionTime} ms</strong></span>
            </div>
          )}
        </div>
      )}

      {/* Job Postings Stream */}
      <div className="jobs-list">
        {!loading && results.length === 0 && hasSearched && (
          <div className="empty-state">
            <div style={{ display: 'inline-flex', padding: '12px', background: '#eff6ff', borderRadius: '50%', marginBottom: '1rem', color: '#2563eb' }}>
              <ShieldCheck size={36} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1e293b', marginBottom: '0.5rem' }}>
              Relevance Guardrail Active • 0 Jobs Matched
            </h3>
            <p style={{ color: '#475569', maxWidth: '520px', margin: '0 auto 1rem', lineHeight: '1.5' }}>
              Query <strong>"{query}"</strong> has no relevant positions in our technical index.
            </p>
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '14px 18px', maxWidth: '580px', margin: '0 auto', textAlign: 'left', fontSize: '0.875rem' }}>
              <div style={{ fontWeight: 600, color: '#334155', marginBottom: '8px' }}>
                Why were results suppressed?
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.2rem', color: '#64748b', lineHeight: '1.6' }}>
                <li>
                  <strong>BM25 Keyword Match:</strong> Score is 0.0 (the word <em>"{query}"</em> does not exist in any job posting).
                </li>
                <li>
                  <strong>pgvector Semantic Match:</strong> The nearest job vectors were below our <strong>0.23 (23%)</strong> similarity threshold.
                </li>
                <li>
                  <strong>Hallucination Prevention:</strong> Without this guardrail, pure KNN vector search blindly returns the nearest 10 jobs even if completely unrelated (e.g. returning software roles for "maid" or "banana"). Our threshold safely filters out out-of-domain noise.
                </li>
              </ul>
            </div>
          </div>
        )}

        {results.map((r, index) => {
          const avatarGradient = COMPANY_COLORS[r.company] || 'linear-gradient(135deg, #4f46e5, #7c3aed)';
          const companyInitial = r.company ? r.company.substring(0, 1).toUpperCase() : 'J';

          // Score display depending on the active retrieval mode
          let scorePrimary = '';
          let scoreLabel = '';
          if (mode === 'bm25') {
            scorePrimary = r.bm25_score.toFixed(2);
            scoreLabel = 'BM25 Score';
          } else if (mode === 'vector') {
            scorePrimary = `${Math.round(r.vector_score * 100)}%`;
            scoreLabel = `Cosine ${r.vector_score.toFixed(4)}`;
          } else {
            // Hybrid
            const maxTheoretical = 0.0328;
            const pct = Math.min(100, Math.round((r.score / maxTheoretical) * 100));
            scorePrimary = `${pct}% Match`;
            scoreLabel = `RRF ${r.score.toFixed(4)}`;
          }

          return (
            <div key={r.job_id || index} className="job-card">
              <div className="job-header">
                <div className="job-identity">
                  {/* Company Monogram Badge */}
                  <div
                    className="company-avatar"
                    style={{ background: avatarGradient }}
                    title={r.company}
                  >
                    {companyInitial}
                  </div>
                  <div>
                    <div className="job-title-row">
                      <span className="rank-badge">#{index + 1}</span>
                      <h3 className="job-title">{r.title}</h3>
                    </div>
                    <div className="job-company">{r.company}</div>
                  </div>
                </div>

                {/* Score Visual Gauge */}
                <div className="score-badge">
                  <span className="score-main">{scorePrimary}</span>
                  <span className="score-sub">{scoreLabel}</span>
                </div>
              </div>

              {/* Metadata Details Row */}
              <div className="job-details-row">
                <span className="detail-item">
                  <MapPin size={15} /> {r.location}
                </span>
                <span className="detail-item">
                  <Briefcase size={15} /> {r.experience} • {r.employment_type}
                </span>
                {r.salary && (
                  <span className="detail-item">
                    <DollarSign size={15} /> {r.salary}
                  </span>
                )}
              </div>

              {/* Component breakdown badges in Hybrid mode */}
              <div className="sources-pills">
                {r.sources.map((src) => (
                  <span
                    key={src}
                    className={`source-pill ${
                      src === 'BM25' ? 'source-bm25' : 'source-vector'
                    }`}
                  >
                    {src === 'BM25' ? (
                      <>
                        <Zap size={12} /> BM25 Keyword
                      </>
                    ) : (
                      <>
                        <Brain size={12} /> pgvector Semantic
                      </>
                    )}
                  </span>
                ))}

                {mode === 'hybrid' && r.bm25_rank && (
                  <span className="component-rank-tag">
                    <Hash size={11} /> BM25 Rank #{r.bm25_rank}
                  </span>
                )}

                {mode === 'hybrid' && r.vector_rank && (
                  <span className="component-rank-tag">
                    <Hash size={11} /> Vector Rank #{r.vector_rank}
                  </span>
                )}
              </div>

              {/* Skills Tags */}
              <div className="skills-container">
                {r.skills.map((skill) => {
                  const isMatched = (r.matched_skills || []).includes(skill);
                  return (
                    <span
                      key={skill}
                      className={`skill-tag ${isMatched ? 'skill-tag-matched' : ''}`}
                    >
                      {skill}
                    </span>
                  );
                })}
              </div>

              {/* ─── IN-DEPTH WHY RETRIEVED EXPLANATION BOX ─── */}
              {r.why_matched && (
                <div className="why-matched-box">
                  <div className="why-matched-header">
                    <Sparkles size={14} /> Why this job appeared in search:
                  </div>
                  <div className="why-matched-text">{r.why_matched}</div>
                </div>
              )}

              {/* Description Preview */}
              <p className="job-description">
                {r.description.length > 250
                  ? r.description.substring(0, 250) + '...'
                  : r.description}
              </p>

              {/* Actions */}
              <div className="job-actions">
                <a
                  href={r.application_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="apply-btn"
                >
                  <span>Apply Now</span>
                  <ExternalLink size={15} />
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
