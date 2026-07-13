import { useState, useRef } from 'react'
import { useRouter } from 'next/router'

const INSTITUTIONS = [
  { id: 'Lokayuktha', name: 'Lokayuktha', desc: 'Corruption & govt inaction complaints' },
  { id: 'National Human Rights Commission (NHRC)', name: 'NHRC', desc: 'Human rights violations by state' },
  { id: 'State Women\'s Commission', name: "Women's Commission", desc: "Women's rights & safety issues" },
  { id: 'District Consumer Forum', name: 'Consumer Forum', desc: 'Consumer disputes & deficiency of service' },
  { id: 'District Court', name: 'District Court', desc: 'Civil & criminal matters' },
  { id: 'State Human Rights Commission (SHRC)', name: 'SHRC', desc: 'State-level human rights body' },
  { id: 'RTI Officer (Right to Information)', name: 'RTI Application', desc: 'Seeking information from govt' },
  { id: 'Labour Commissioner', name: 'Labour Commissioner', desc: 'Workplace disputes & wages' },
]

const DRAFT_TYPES = [
  'Initial Complaint',
  'Reply / Counter',
  'Follow-up Reminder',
  'Rejoinder',
  'Appeal',
  'Legal Notice',
]

export default function Home() {
  const router = useRouter()

  function logout() {
    localStorage.removeItem('lexflow_token')
    router.push('/login')
  }
  const [institution, setInstitution] = useState('Lokayuktha')
  const [draftType, setDraftType] = useState('Initial Complaint')
  const [complaint, setComplaint] = useState('')
  const [petitionerName, setPetitionerName] = useState('')
  const [respondentName, setRespondentName] = useState('')
  const [location, setLocation] = useState('')
  const [extraContext, setExtraContext] = useState('')

  const [extractedText, setExtractedText] = useState('')
  const [fileName, setFileName] = useState('')
  const [pdfPreview, setPdfPreview] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [draftOutput, setDraftOutput] = useState('')
  const [showOutput, setShowOutput] = useState(false)
  const [showLoadingBar, setShowLoadingBar] = useState(false)
  const [isDraftReady, setIsDraftReady] = useState(false)
  const [stageLabel, setStageLabel] = useState('')
  const [compliance, setCompliance] = useState(null)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])

  const fileInputRef = useRef(null)
  const outputRef = useRef(null)

  async function handleFile(file) {
    if (!file) return
    setFileName(file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)')
    setPdfPreview('Extracting text...')
    setExtractedText('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/ai/extract-pdf', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Extraction failed')
      setExtractedText(data.text || '')
      setPdfPreview(data.warning || (data.text ? data.text.substring(0, 600) + (data.text.length > 600 ? '...' : '') : 'No text found.'))
    } catch (e) {
      setPdfPreview('Could not extract file. You can still type your complaint below.')
    }
  }

  function onFileChange(e) {
    if (e.target.files[0]) handleFile(e.target.files[0])
  }

  function onDragOver(e) { e.preventDefault(); setIsDragging(true) }
  function onDragLeave() { setIsDragging(false) }
  function onDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])
  }

  async function generateDraft() {
    if (!complaint && !extractedText) {
      setError('Please describe your complaint or upload a case file first.')
      return
    }

    setError('')
    setIsLoading(true)
    setIsStreaming(true)
    setShowOutput(true)
    setShowLoadingBar(true)
    setIsDraftReady(false)
    setDraftOutput('')
    setCompliance(null)
    setStageLabel('Starting pipeline...')

    try {
      const token = localStorage.getItem('lexflow_token') || ''
      const res = await fetch('/api/ai/draft-v2', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          institution,
          draft_type: draftType,
          complaint,
          extracted_pdf_text: extractedText,
          petitioner_name: petitionerName,
          respondent_name: respondentName,
          location,
          extra_context: extraContext,
        }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Draft generation failed.')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      let draftStarted = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const parsed = JSON.parse(line.slice(6))
            if (parsed.type === 'stage') {
              setStageLabel(parsed.payload)
              if (!draftStarted) setShowLoadingBar(true)
            } else if (parsed.type === 'text') {
              if (!draftStarted) {
                draftStarted = true
                setShowLoadingBar(false)
              }
              fullText += parsed.payload
              setDraftOutput(fullText)
              if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight
            } else if (parsed.type === 'compliance') {
              setCompliance(parsed.payload)
            } else if (parsed.type === 'done') {
              setIsDraftReady(true)
              setStageLabel('')
              setHistory(prev => [{ type: draftType, inst: institution, text: fullText, time: new Date().toLocaleTimeString('en-IN') }, ...prev].slice(0, 5))
            } else if (parsed.type === 'error') {
              throw new Error(parsed.payload)
            }
          } catch (parseErr) {
            if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr
          }
        }
      }
    } catch (e) {
      setShowLoadingBar(false)
      setShowOutput(false)
      setStageLabel('')
      setError(e.message)
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
    }
  }

  function copyDraft() {
    navigator.clipboard.writeText(draftOutput).then(() => alert('Draft copied to clipboard!'))
  }

  function downloadDraft() {
    const blob = new Blob([draftOutput], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `LexFlow_Draft_${institution.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
  }

  function printDraft() {
    const win = window.open('', '_blank')
    win.document.write(`<html><head><title>Legal Draft - ${institution}</title><style>
      body{font-family:Georgia,serif;max-width:700px;margin:40px auto;font-size:14px;line-height:1.8;color:#111}
      pre{white-space:pre-wrap;font-family:inherit}
      h3{text-align:center;border-bottom:2px solid #000;padding-bottom:8px;margin-bottom:20px}
    </style></head><body>
    <h3>LEGAL DRAFT — ${institution.toUpperCase()}</h3>
    <pre>${draftOutput}</pre>
    <br><br><p style="font-size:11px;color:#888;border-top:1px solid #ccc;padding-top:8px">Generated by LexFlow AI — For reference only. Please review with a qualified advocate.</p>
    </body></html>`)
    win.document.close()
    win.print()
  }

  function loadHistory(item) {
    setDraftOutput(item.text)
    setShowOutput(true)
    setIsDraftReady(true)
    setInstitution(item.inst)
    setDraftType(item.type)
  }

  const uploadZoneClass = ['upload-zone', isDragging ? 'drag' : '', fileName ? 'has-file' : ''].filter(Boolean).join(' ')

  return (
    <>
      <header>
        <div className="logo">
          ⚖️ LexFlow AI
          <span className="logo-badge">MVP</span>
        </div>
        <div className="header-right">
          <div className="api-indicator">
            <div className="dot dot-green" />
            <span>Backend Connected</span>
          </div>
          <span>Legal Draft Assistant</span>
          <button
            onClick={logout}
            style={{ background: 'none', border: '1px solid #3a3830', borderRadius: 6, color: '#9a9490', fontSize: 12, padding: '4px 10px', cursor: 'pointer', fontFamily: 'inherit' }}
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="main">
        <div className="page-title">Legal Draft Generator</div>
        <div className="page-sub">Upload a case file or describe your situation — get a professionally drafted legal reply in seconds</div>

        <div className="grid">

          {/* LEFT — INPUTS */}
          <div>

            {/* UPLOAD */}
            <div className="card mb-20">
              <div className="card-title">📄 Case File</div>
              <div className="card-sub">Upload existing FIR, order, or notice (PDF). Optional — you can also type below.</div>
              <div
                className={uploadZoneClass}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
              >
                <div className="upload-icon">📂</div>
                <div className="upload-text"><strong>Click to upload</strong> or drag &amp; drop</div>
                <div className="upload-text" style={{ fontSize: 11, marginTop: 4 }}>PDF or TXT files up to 10MB</div>
                <input ref={fileInputRef} type="file" accept=".pdf,.txt" style={{ display: 'none' }} onChange={onFileChange} />
              </div>
              {fileName && <div className="file-info">✓ {fileName}</div>}
              {pdfPreview && <div className="pdf-preview">{pdfPreview}</div>}
            </div>

            {/* COMPLAINT */}
            <div className="card mb-20">
              <div className="card-title">✍️ Your Complaint / Situation</div>
              <div className="card-sub">Describe what happened in plain language. Telugu or Hindi also works.</div>
              <textarea
                rows={5}
                value={complaint}
                onChange={e => setComplaint(e.target.value)}
                placeholder="Example: My neighbour encroached on my land in 2022. I gave police complaint in Jan 2023 but no action was taken..."
              />
              <div className="char-count">{complaint.length} characters</div>
            </div>

            {/* PETITIONER DETAILS */}
            <div className="card mb-20">
              <div className="card-title">👤 Petitioner Details</div>
              <div className="card-sub">Basic info for the draft (optional — leave blank for template)</div>
              <div className="two-col">
                <div>
                  <label className="label">Your Name</label>
                  <input className="context-input" type="text" value={petitionerName} onChange={e => setPetitionerName(e.target.value)} placeholder="Full name" />
                </div>
                <div>
                  <label className="label">Respondent / Opposite Party</label>
                  <input className="context-input" type="text" value={respondentName} onChange={e => setRespondentName(e.target.value)} placeholder="Person / authority name" />
                </div>
              </div>
              <div>
                <label className="label">District / Location</label>
                <input className="context-input" type="text" value={location} onChange={e => setLocation(e.target.value)} placeholder="e.g. Hyderabad, Telangana" />
              </div>
            </div>

          </div>

          {/* RIGHT — SETTINGS */}
          <div>

            {/* INSTITUTION */}
            <div className="card mb-20">
              <div className="card-title">🏛️ Select Institution</div>
              <div className="card-sub">Where will this document be submitted?</div>
              <div className="inst-grid">
                {INSTITUTIONS.map(inst => (
                  <button
                    key={inst.id}
                    className={`inst-btn${institution === inst.id ? ' selected' : ''}`}
                    onClick={() => setInstitution(inst.id)}
                  >
                    <div className="inst-name">{inst.name}</div>
                    <div className="inst-desc">{inst.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* DRAFT TYPE */}
            <div className="card mb-20">
              <div className="card-title">📝 Document Type</div>
              <div className="card-sub">What kind of document do you need?</div>
              <div className="draft-grid">
                {DRAFT_TYPES.map(type => (
                  <button
                    key={type}
                    className={`draft-btn${draftType === type ? ' selected' : ''}`}
                    onClick={() => setDraftType(type)}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {/* ADDITIONAL INSTRUCTIONS */}
            <div className="card mb-20">
              <div className="card-title">🎯 Additional Instructions</div>
              <div className="card-sub">Any specific points to emphasise or sections to include?</div>
              <textarea
                rows={3}
                value={extraContext}
                onChange={e => setExtraContext(e.target.value)}
                placeholder="e.g. Mention that police have not acted for 8 months. Emphasise urgency due to health condition..."
              />
            </div>

            {/* DRAFT HISTORY */}
            <div className="card">
              <div className="card-title">📋 Draft History</div>
              <div className="card-sub">Recent drafts in this session</div>
              <div className="history-list">
                {history.length === 0
                  ? <div className="no-history">No drafts yet. Generate your first draft below.</div>
                  : history.map((item, i) => (
                    <div key={i} className="history-item" onClick={() => loadHistory(item)}>
                      <div className="history-dot" />
                      <div className="history-text">
                        <div className="history-title">{item.type} → {item.inst}</div>
                        <div className="history-meta">{item.time}</div>
                      </div>
                      <span style={{ fontSize: 11, color: '#bab4aa' }}>▶</span>
                    </div>
                  ))
                }
              </div>
            </div>

          </div>
        </div>

        {/* ERROR */}
        {error && <div className="error-box">{error}</div>}

        {/* GENERATE */}
        <button className="btn-generate" disabled={isLoading} onClick={generateDraft}>
          {isLoading && <div className="spinner" />}
          <span>{isLoading ? 'Drafting...' : '⚡ Generate Legal Draft'}</span>
          <div className="gold-line" />
        </button>

        {/* OUTPUT */}
        {showOutput && (
          <div style={{ marginTop: 28 }}>
            {showLoadingBar && (
              <div className="loading-bar">
                <div className="loading-fill" />
              </div>
            )}

            {stageLabel && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, fontSize: 13, color: 'var(--muted)' }}>
                <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                {stageLabel}
              </div>
            )}

            <div className="output-header">
              <div className="output-title">
                📜 Generated Draft
                {isDraftReady && <span className="success-pill">✓ Ready</span>}
              </div>
              {isDraftReady && (
                <div className="output-actions">
                  <button className="btn-action" onClick={copyDraft}>📋 Copy</button>
                  <button className="btn-action" onClick={downloadDraft}>⬇ Download</button>
                  <button className="btn-action primary" onClick={printDraft}>🖨️ Print</button>
                </div>
              )}
            </div>

            <div className="draft-doc">
              <div className="draft-doc-header">
                <span>{draftType.toUpperCase()} — {institution.toUpperCase()}</span>
                <span>{new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
              </div>
              <div className="draft-doc-body" ref={outputRef}>
                {draftOutput}
                {isStreaming && <span className="cursor" />}
              </div>
            </div>

            {/* COMPLIANCE REPORT */}
            {compliance && (
              <div style={{ marginTop: 14, padding: '14px 18px', background: compliance.passed ? '#f0faf4' : '#fff8f0', border: `1px solid ${compliance.passed ? '#b5d9c3' : '#f5d5a0'}`, borderRadius: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: compliance.passed ? 'var(--green)' : '#8b5c00' }}>
                  {compliance.passed ? '✓ Compliance check passed' : '⚠ Compliance issues found'}
                </div>
                {compliance.issues?.length > 0 && (
                  <ul style={{ fontSize: 12, color: 'var(--red)', margin: '4px 0 8px 16px' }}>
                    {compliance.issues.map((issue, i) => <li key={i}>{issue}</li>)}
                  </ul>
                )}
                {compliance.warnings?.length > 0 && (
                  <ul style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0 0 16px' }}>
                    {compliance.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                )}
              </div>
            )}

            <div className="footer-note" style={{ marginTop: 16 }}>
              ⚠️ <strong>Disclaimer:</strong> This draft is AI-generated and for reference only. Please review with a qualified advocate before submission. LexFlow AI does not provide legal advice.
            </div>
          </div>
        )}

        <div className="footer-note">
          <strong>How to use:</strong> Upload a case file or describe your situation → select the institution and document type → click Generate. The draft will stream in real time. You can copy, download or print it directly.
        </div>
      </div>
    </>
  )
}
