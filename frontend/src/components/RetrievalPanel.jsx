import React, { useState } from 'react';

function DocumentCard({ document }) {
  const [expanded, setExpanded] = useState(false);
  const metadata = document.metadata || {};
  const article = metadata.article ?? metadata.article_number ?? 'N/A';
  const chapter = metadata.chapter || metadata.chapter_title || '';

  return (
    <div className={`doc-card ${expanded ? 'expanded' : ''}`} onClick={() => setExpanded((current) => !current)}>
      <div className="doc-meta">
        <div className="doc-meta-row">
          <span className="doc-law-id">{metadata.law_id || metadata.document_short_name || 'DOCUMENT'}</span>
          <span className="doc-score">Score: {(document.total_score || 0).toFixed(4)}</span>
        </div>
        <div className="doc-sub-scores">
          <span>Sparse: {(document.sparse_score || 0).toFixed(4)}</span>
          <span>Dense: {(document.dense_score || 0).toFixed(4)}</span>
        </div>
      </div>
      <span className="doc-title">{metadata.title || metadata.article_title || 'Untitled Section'}</span>
      <div className="doc-content">{document.text || 'No content available.'}</div>
      <div className="doc-tags">
        {chapter && <span className="doc-tag">{chapter}</span>}
        {article !== 'N/A' && <span className="doc-tag">Article {article}</span>}
      </div>
    </div>
  );
}

export default function RetrievalPanel({ documents }) {
  return (
    <aside className="retrieval-panel">
      <div className="panel-header">Knowledge Base (RAG)</div>
      <div className="doc-list">
        {documents.length === 0 ? (
          <div className="empty-docs">No documents retrieved yet.</div>
        ) : (
          documents.map((document, index) => (
            <DocumentCard key={`${document.text || 'doc'}-${index}`} document={document} />
          ))
        )}
      </div>
    </aside>
  );
}