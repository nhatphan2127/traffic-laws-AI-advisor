import React, { useState } from 'react';

export default function ThinkingConsole({ thinking, loading }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div className="thinking-console">
      <button className="console-header" type="button" onClick={() => setExpanded((current) => !current)}>
        <span>AGENT_REASONING_LOG</span>
        <span>{expanded ? '[-] Collapse Logs' : '[+] Expand Logs'}</span>
      </button>
      {expanded && <div className="console-body show">{thinking}</div>}
      {loading && <div className="loading-line" />}
    </div>
  );
}