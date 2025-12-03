import React, { useState } from 'react'

export default function SearchResults({ items, onDownload, onClear }) {
  const [page, setPage] = useState(1)
  const pageSize = 5
  const totalPages = Math.ceil((items?.length || 0) / pageSize)
  const pagedItems = items?.slice((page - 1) * pageSize, page * pageSize) || []

  if (!items || items.length === 0) {
    return <div className="card"><p className="empty">No results yet.</p></div>
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Results</h3>
        <button onClick={onClear} style={{ fontSize: 12, padding: '2px 10px', borderRadius: 8, background: '#26306b', color: '#fff', border: 'none', cursor: 'pointer' }}>Clear</button>
      </div>
      {pagedItems.map(it => (
        <div key={it.id} className="row space" style={{ marginBottom: 10 }}>
          <div>
            <div style={{ fontWeight: 600 }}>{it.filename}</div>
            <div style={{ fontSize: 12, color: '#99a3ff' }}>
              {Array.isArray(it.tags) && it.tags.slice(0,6).map(t => (
                <span key={t} style={{ marginRight: 8, background:'#0a0f22', padding:'2px 8px', borderRadius: 10, border:'1px solid #26306b' }}>{t}</span>
              ))}
            </div>
          </div>
          <button onClick={() => onDownload(it.id)}>Download</button>
        </div>
      ))}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginTop: 10 }}>
        <button
          onClick={() => setPage(page - 1)}
          disabled={page === 1}
          style={{ marginRight: 8, padding: '2px 8px', borderRadius: 6, border: '1px solid #26306b', background: '#0a0f22', color: '#fff', cursor: page === 1 ? 'not-allowed' : 'pointer' }}
        >Prev</button>
        <span style={{ fontSize: 13, margin: '0 8px' }}>Page {page} of {totalPages}</span>
        <button
          onClick={() => setPage(page + 1)}
          disabled={page === totalPages}
          style={{ marginLeft: 8, padding: '2px 8px', borderRadius: 6, border: '1px solid #26306b', background: '#0a0f22', color: '#fff', cursor: page === totalPages ? 'not-allowed' : 'pointer' }}
        >Next</button>
      </div>
    </div>
  )
}