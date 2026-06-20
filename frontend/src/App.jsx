import React, { useState, useEffect, useRef } from 'react'
import { 
  Send, 
  Terminal as TerminalIcon, 
  Dna, 
  BookOpen, 
  Clipboard, 
  Activity, 
  CheckCircle,
  AlertCircle,
  FileText,
  MapPin,
  ChevronRight,
  ExternalLink
} from 'lucide-react'

const EXAMPLES = [
  {
    title: "Lung Cancer (EGFR)",
    query: "58yo male diagnosed with non-small cell lung cancer with EGFR T790M mutation in California"
  },
  {
    title: "Breast Cancer (BRCA1)",
    query: "45-year-old female with BRCA1 positive breast cancer near Boston"
  },
  {
    title: "Melanoma (BRAF)",
    query: "Melanoma patient, BRAF V600E mutation, looking for clinical trials in Texas"
  }
]

export default function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState([])
  const [results, setResults] = useState(null)
  const [activeTab, setActiveTab] = useState('synthesis')
  const consoleEndRef = useRef(null)

  const [isVerificationMode, setIsVerificationMode] = useState(false)
  const [editedSynthesis, setEditedSynthesis] = useState('')
  const [approvedTrials, setApprovedTrials] = useState([])
  const [approvedGenomics, setApprovedGenomics] = useState([])
  const [approvedLiterature, setApprovedLiterature] = useState([])
  const [physicianName, setPhysicianName] = useState('')
  const [licenseNumber, setLicenseNumber] = useState('')
  const [exportingPdf, setExportingPdf] = useState(false)

  const API_BASE = import.meta.env.VITE_API_URL || '';

  const toggleTrialApproval = (trial) => {
    setApprovedTrials(prev => {
      const exists = prev.some(t => t.nct_id === trial.nct_id);
      if (exists) {
        return prev.filter(t => t.nct_id !== trial.nct_id);
      } else {
        return [...prev, trial];
      }
    });
  }

  const toggleGenomicApproval = (variant) => {
    setApprovedGenomics(prev => {
      const exists = prev.some(g => g.variant === variant.variant);
      if (exists) {
        return prev.filter(g => g.variant !== variant.variant);
      } else {
        return [...prev, variant];
      }
    });
  }

  const toggleLiteratureApproval = (art) => {
    setApprovedLiterature(prev => {
      const exists = prev.some(l => l.pmid === art.pmid);
      if (exists) {
        return prev.filter(l => l.pmid !== art.pmid);
      } else {
        return [...prev, art];
      }
    });
  }

  const handleExportPDF = async () => {
    if (!physicianName.trim() || !licenseNumber.trim()) {
      alert("Please fill in Physician Name and License Number to sign off the report.");
      return;
    }
    
    setExportingPdf(true);
    try {
      const response = await fetch(`${API_BASE}/api/export-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          physician_name: physicianName,
          license_number: licenseNumber,
          patient_query: query,
          edited_synthesis: editedSynthesis,
          approved_trials: approvedTrials,
          approved_genomics: approvedGenomics,
          approved_literature: approvedLiterature
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate PDF');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Clinical_Report_${physicianName.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Error exporting PDF: ${err.message}`);
    } finally {
      setExportingPdf(false);
    }
  }

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs])

  const triggerSearch = async (searchQuery) => {
    if (!searchQuery.strip && !searchQuery.trim()) return
    
    setLoading(true)
    setLogs([])
    setResults(null)
    setActiveTab('synthesis')

    try {
      const response = await fetch(`${API_BASE}/api/intake`, {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: searchQuery }),
      })

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        
        // Save the last partial line back to the buffer
        buffer = lines.pop()

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue
          
          try {
            const rawJson = trimmed.slice(6) // remove 'data: '
            const event = JSON.parse(rawJson)
            
            if (event.status === 'processing' || event.status === 'completed') {
              setLogs(prev => [...prev, {
                agent: event.agent,
                message: event.message,
                status: event.status
              }])
            } else if (event.status === 'result') {
              setResults(event.data)
              setEditedSynthesis(event.data.synthesis || '')
              setApprovedTrials(event.data.clinical_trials || [])
              setApprovedGenomics(event.data.genomics || [])
              setApprovedLiterature(event.data.literature || [])
            } else if (event.status === 'error') {
              setLogs(prev => [...prev, {
                agent: 'CoordinatorAgent',
                message: event.message,
                status: 'error'
              }])
            }
          } catch (e) {
            console.error('Failed to parse SSE event JSON:', e)
          }
        }
      }
    } catch (error) {
      setLogs(prev => [...prev, {
        agent: 'CoordinatorAgent',
        message: `Network/API Error: ${error.message}. Please check if the FastAPI backend is running on port 8000.`,
        status: 'error'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    triggerSearch(query)
  }

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <div className="brand">
          <Activity className="brand-logo" size={32} />
          <div>
            <h1>ClinicaAgent</h1>
            <p className="subtitle">Intelligent Multi-Agent Clinical & Genomic Intelligence Platform</p>
          </div>
        </div>
        <div className="track-badge glass-panel" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', color: '#00f2fe', borderColor: 'rgba(0, 242, 254, 0.3)' }}>
          Kaggle Capstone - Agents for Good
        </div>
      </header>

      {/* Main Grid */}
      <div className="dashboard-grid">
        
        {/* Left Side: Query Intake & Live Logs */}
        <div className="flex-col" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          
          {/* Intake Card */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={20} color="#00f2fe" />
              Patient Profile Intake
            </h2>
            
            <form onSubmit={handleSubmit}>
              <div className="input-group">
                <label className="input-label" htmlFor="patient-query">
                  Describe symptoms, primary diagnosis, location, and genetic mutations:
                </label>
                <textarea
                  id="patient-query"
                  className="text-area-custom"
                  placeholder="e.g., 55yo female diagnosed with stage IV non-small cell lung cancer, EGFR T790M positive, seeking trials in California..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={loading}
                />
              </div>
              
              <button 
                type="submit" 
                className={`btn-primary ${loading ? 'pulse-glow' : ''}`}
                disabled={loading || !query.trim()}
              >
                {loading ? (
                  <>
                    <Activity size={18} className="animate-spin" />
                    Running Agents...
                  </>
                ) : (
                  <>
                    <Send size={18} />
                    Submit to Orchestrator
                  </>
                )}
              </button>
            </form>

            <div style={{ marginTop: '1.5rem' }}>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Try these example profiles:</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {EXAMPLES.map((ex, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setQuery(ex.query);
                      triggerSearch(ex.query);
                    }}
                    disabled={loading}
                    className="glass-panel"
                    style={{
                      padding: '0.65rem 0.85rem',
                      textAlign: 'left',
                      fontSize: '0.8rem',
                      background: 'rgba(255,255,255,0.02)',
                      cursor: 'pointer',
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      borderRadius: '8px'
                    }}
                  >
                    <span><strong>{ex.title}:</strong> {ex.query.substring(0, 50)}...</span>
                    <ChevronRight size={14} color="#00f2fe" />
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Real-time Agent Log Console */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <TerminalIcon size={20} color="#fbbf24" />
              Agent Activity Console
            </h2>
            
            <div className="console-panel">
              {logs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', padding: '1rem 0' }}>
                  Awaiting query submission to trigger agents...
                </div>
              ) : (
                logs.map((log, idx) => (
                  <div key={idx} className="log-entry">
                    <span className={`agent-badge agent-${log.agent}`}>{log.agent.replace('Agent', '')}</span>
                    <span style={{ color: log.status === 'error' ? '#f87171' : 'var(--text-main)' }}>{log.message}</span>
                  </div>
                ))
              )}
              {loading && (
                <div className="log-entry" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#00f2fe' }}>
                  <Activity size={12} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Sub-agents executing tasks in background...</span>
                </div>
              )}
              <div ref={consoleEndRef} />
            </div>
          </div>

        </div>

        {/* Right Side: Tabbed Results Display */}
        <div className="glass-panel" style={{ padding: '1.5rem', minHeight: '500px' }}>
          {!results ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              height: '100%',
              color: 'var(--text-muted)',
              textAlign: 'center',
              padding: '4rem 1rem'
            }}>
              <Activity size={48} style={{ color: 'rgba(0, 242, 254, 0.15)', marginBottom: '1.5rem' }} />
              <h3 style={{ fontSize: '1.2rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>No Analysis Results</h3>
              <p style={{ maxWidth: '400px', fontSize: '0.9rem' }}>
                Fill out the Patient Profile on the left and submit to launch the agent workflow. Results will load here once the synthesis is complete.
              </p>
            </div>
          ) : (
            <div className="results-container">
              
              {/* Verification Toggle Bar */}
              <div className="verification-bar glass-panel">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <input
                    type="checkbox"
                    id="verification-toggle"
                    checked={isVerificationMode}
                    onChange={(e) => setIsVerificationMode(e.target.checked)}
                    style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                  <label htmlFor="verification-toggle" style={{ fontWeight: '600', cursor: 'pointer', fontSize: '0.85rem', color: isVerificationMode ? '#00f2fe' : 'var(--text-main)' }}>
                    {isVerificationMode ? '🟢 Verification Mode: ACTIVE' : '⚪ Enable Doctor Verification Hub'}
                  </label>
                </div>
                
                {isVerificationMode && (
                  <div className="physician-inputs" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input
                      type="text"
                      placeholder="Dr. Name"
                      value={physicianName}
                      onChange={(e) => setPhysicianName(e.target.value)}
                      className="text-input-custom"
                      style={{ maxWidth: '140px', padding: '0.4rem 0.6rem', fontSize: '0.8rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                    />
                    <input
                      type="text"
                      placeholder="License #"
                      value={licenseNumber}
                      onChange={(e) => setLicenseNumber(e.target.value)}
                      className="text-input-custom"
                      style={{ maxWidth: '110px', padding: '0.4rem 0.6rem', fontSize: '0.8rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                    />
                    <button
                      onClick={handleExportPDF}
                      disabled={exportingPdf}
                      className="btn-primary"
                      style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', whiteSpace: 'nowrap', minHeight: 'auto', margin: 0 }}
                    >
                      {exportingPdf ? 'Exporting...' : 'Export Verified PDF'}
                    </button>
                  </div>
                )}
              </div>

              {/* Tab Navigation */}
              <div className="results-header-tabs" style={{ marginTop: '1rem' }}>
                <button 
                  onClick={() => setActiveTab('synthesis')}
                  className={`tab-btn ${activeTab === 'synthesis' ? 'active' : ''}`}
                >
                  <Clipboard size={16} />
                  Clinical Synthesis
                </button>
                <button 
                  onClick={() => setActiveTab('trials')}
                  className={`tab-btn ${activeTab === 'trials' ? 'active' : ''}`}
                >
                  <BookOpen size={16} />
                  Clinical Trials ({results.clinical_trials.length})
                </button>
                <button 
                  onClick={() => setActiveTab('genomics')}
                  className={`tab-btn ${activeTab === 'genomics' ? 'active' : ''}`}
                >
                  <Dna size={16} />
                  Genomic Variations ({results.genomics.length})
                </button>
                <button 
                  onClick={() => setActiveTab('literature')}
                  className={`tab-btn ${activeTab === 'literature' ? 'active' : ''}`}
                >
                  <BookOpen size={16} />
                  PubMed Articles ({results.literature.length})
                </button>
              </div>

              {/* Tab Content Panels */}
              <div className="tab-panel-content" style={{ marginTop: '0.5rem' }}>
                
                {/* 1. Synthesis Tab */}
                {activeTab === 'synthesis' && (
                  <div className="synthesis-box">
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                      <CheckCircle size={20} color="#00f2fe" />
                      Orchestrator Medical Report
                    </h3>
                    {isVerificationMode ? (
                      <textarea
                        className="text-area-custom"
                        style={{ minHeight: '300px', fontSize: '0.9rem', lineHeight: '1.4', width: '100%', background: 'rgba(0,0,0,0.2)', padding: '1rem', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '8px' }}
                        value={editedSynthesis}
                        onChange={(e) => setEditedSynthesis(e.target.value)}
                      />
                    ) : (
                      <div 
                        style={{ fontSize: '0.95rem', whiteSpace: 'pre-line' }} 
                        dangerouslySetInnerHTML={{ __html: formatReportMarkup(editedSynthesis) }} 
                      />
                    )}
                  </div>
                )}

                {/* 2. Clinical Trials Tab */}
                {activeTab === 'trials' && (
                  <div className="card-list">
                    {results.clinical_trials.length === 0 ? (
                      <div style={{ color: 'var(--text-muted)', padding: '2rem 0', textAlign: 'center' }}>
                        No matching clinical trials found.
                      </div>
                    ) : (
                      results.clinical_trials.map((trial, idx) => {
                        const isApproved = approvedTrials.some(t => t.nct_id === trial.nct_id);
                        return (
                          <div key={idx} className={`item-card ${isVerificationMode ? (isApproved ? 'approved-card' : 'excluded-card') : ''}`} style={{ transition: 'all 0.2s ease' }}>
                            <div className="card-title-row">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                                {isVerificationMode && (
                                  <input
                                    type="checkbox"
                                    checked={isApproved}
                                    onChange={() => toggleTrialApproval(trial)}
                                    style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                                  />
                                )}
                                <h4 className="card-title">{trial.title}</h4>
                              </div>
                              <span className="card-badge">{trial.phase}</span>
                            </div>
                            <div className="card-subtitle">{trial.nct_id} | Sponsor: {trial.sponsor}</div>
                            <p className="card-desc">{trial.summary}</p>
                            
                            {trial.locations.length > 0 && (
                              <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center', fontSize: '0.8rem', color: '#34d399', marginBottom: '0.75rem' }}>
                                <MapPin size={12} />
                                <span>Locations: {trial.locations.join('; ')}</span>
                              </div>
                            )}

                            <div className="card-footer">
                              <span>Target Age: {trial.age_range} | Gender: {trial.gender_requirement}</span>
                              <a href={trial.url} target="_blank" rel="noopener noreferrer" className="card-link">
                                View Trial <ExternalLink size={12} />
                              </a>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}

                {/* 3. Genomics Tab */}
                {activeTab === 'genomics' && (
                  <div className="card-list">
                    {results.genomics.length === 0 ? (
                      <div style={{ color: 'var(--text-muted)', padding: '2rem 0', textAlign: 'center' }}>
                        No genetic variants analyzed for this profile.
                      </div>
                    ) : (
                      results.genomics.map((varData, idx) => {
                        const isApproved = approvedGenomics.some(g => g.variant === varData.variant);
                        return (
                          <div key={idx} className={`item-card ${isVerificationMode ? (isApproved ? 'approved-card' : 'excluded-card') : ''}`} style={{ transition: 'all 0.2s ease' }}>
                            <div className="card-title-row">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                                {isVerificationMode && (
                                  <input
                                    type="checkbox"
                                    checked={isApproved}
                                    onChange={() => toggleGenomicApproval(varData)}
                                    style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                                  />
                                )}
                                <h4 className="card-title">{varData.variant}</h4>
                              </div>
                              <span className={`card-badge`} style={{
                                background: varData.clinical_significance?.toLowerCase().includes('pathogenic') ? 'rgba(239, 68, 68, 0.1)' : 'rgba(167, 139, 250, 0.1)',
                                color: varData.clinical_significance?.toLowerCase().includes('pathogenic') ? '#ef4444' : '#a78bfa',
                                borderColor: varData.clinical_significance?.toLowerCase().includes('pathogenic') ? 'rgba(239, 68, 68, 0.2)' : 'rgba(167, 139, 250, 0.2)'
                              }}>
                                {varData.clinical_significance || "Significance Unknown"}
                              </span>
                            </div>
                            
                            {varData.status === "Found" ? (
                              <>
                                <div className="card-subtitle">ClinVar ID: {varData.clinvar_id} | Gene Symbol: {varData.gene}</div>
                                <p className="card-desc"><strong>Database Record:</strong> {varData.title}</p>
                                {varData.locations && varData.locations.length > 0 && (
                                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                                    <strong>Genomic Coordinates:</strong> {varData.locations.join(', ')}
                                  </div>
                                )}
                                <div className="card-footer">
                                  <span />
                                  <a href={varData.url} target="_blank" rel="noopener noreferrer" className="card-link">
                                    NCBI ClinVar Link <ExternalLink size={12} />
                                  </a>
                                </div>
                              </>
                            ) : (
                              <p className="card-desc">{varData.details}</p>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                )}

                {/* 4. PubMed Articles Tab */}
                {activeTab === 'literature' && (
                  <div className="card-list">
                    {results.literature.length === 0 ? (
                      <div style={{ color: 'var(--text-muted)', padding: '2rem 0', textAlign: 'center' }}>
                        No research articles found for this condition.
                      </div>
                    ) : (
                      results.literature.map((art, idx) => {
                        const isApproved = approvedLiterature.some(l => l.pmid === art.pmid);
                        return (
                          <div key={idx} className={`item-card ${isVerificationMode ? (isApproved ? 'approved-card' : 'excluded-card') : ''}`} style={{ transition: 'all 0.2s ease' }}>
                            <div className="card-title-row">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                                {isVerificationMode && (
                                  <input
                                    type="checkbox"
                                    checked={isApproved}
                                    onChange={() => toggleLiteratureApproval(art)}
                                    style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                                  />
                                )}
                                <h4 className="card-title" style={{ marginBottom: '0.5rem' }}>{art.title}</h4>
                              </div>
                            </div>
                            <div className="card-subtitle" style={{ color: 'var(--text-muted)' }}>
                              {art.authors} &bull; {art.journal} ({art.date})
                            </div>
                            
                            <div className="card-footer" style={{ marginTop: '0.75rem' }}>
                              <span style={{ fontSize: '0.8rem' }}>PMID: {art.pmid} {art.pmcid ? `| PMCID: ${art.pmcid}` : ''}</span>
                              <a href={art.url} target="_blank" rel="noopener noreferrer" className="card-link">
                                View Publication <ExternalLink size={12} />
                              </a>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}

              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}

// Utility to bold markdown headers in the synthesized plaintext
function formatReportMarkup(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n\n/g, '<br/><br/>')
}
