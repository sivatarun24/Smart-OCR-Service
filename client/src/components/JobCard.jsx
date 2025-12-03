import React, { useState } from 'react'
import ProgressBar from './ProgressBar'
import { getResult } from '../api'

const pretty = (s) => {
  try { return JSON.stringify(JSON.parse(s), null, 2) } catch { return s }
}

export default function JobCard({ job }) {
  const [open, setOpen] = useState(false)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')
  const [showText, setShowText] = useState(true)
  const [showEntities, setShowEntities] = useState(false)
  const [showTags, setShowTags] = useState(false)

  const fetchResult = async () => {
    setErr('')
    try {
      const r = await getResult(job.job_id)
      setResult(r)
      setOpen(true)
    } catch (e) {
      setErr(e?.response?.data?.error || 'Not ready')
    }
  }

  const Arrow = ({ open }) => (
    <span style={{ cursor: 'pointer', marginRight: 6 }}>
      {open ? '▼' : '▶'}
    </span>
  )

  return (
    <div className="card">
      <div className="row space">
        <div>
          <h3>{job.filename || 'Document'}</h3>
          <p className={`status ${job.status?.toLowerCase()}`}>{job.status} — {job.stage}</p>
        </div>
        <button onClick={fetchResult} disabled={job.status !== 'COMPLETED'}>
          {job.status === 'COMPLETED' ? 'View Result' : 'Processing…'}
        </button>
      </div>
      <ProgressBar value={job.progress || 0} label={job.stage || ''} />
      {err && <p className="error">{err}</p>}
      {open && result && (
        <div className="result">
          <div>
            <h4 style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }} onClick={() => setShowText(v => !v)}>
              <Arrow open={showText} /> Extracted Text
            </h4>
            {showText && <pre className="code">{result.text}</pre>}
          </div>
          <div>
            <h4 style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }} onClick={() => setShowEntities(v => !v)}>
              <Arrow open={showEntities} /> Entities (NER)
            </h4>
            {showEntities && <pre className="code">{pretty(result.entities)}</pre>}
          </div>
          <div>
            <h4 style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }} onClick={() => setShowTags(v => !v)}>
              <Arrow open={showTags} /> Tags
            </h4>
            {showTags && <pre className="code">{pretty(result.tags)}</pre>}
          </div>
        </div>
      )}
    </div>
  )
}