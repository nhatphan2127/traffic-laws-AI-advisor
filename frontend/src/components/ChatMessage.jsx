import React from 'react';
import ThinkingConsole from './ThinkingConsole';
import { renderMarkdown } from '../utils/markdown';

// Ported from the reference app: the backend sometimes emits raw
// tab/space-separated "tables" instead of Markdown tables. This detects
// runs of 2+ lines with tab/multi-space-separated columns and rewrites
// them as a proper Markdown table before handing off to renderMarkdown.
function convertRawTableToMarkdown(text) {
  const lines = text.split('\n');
  const resultLines = [];
  let i = 0;

  const isTableRow = (line) => {
    const trimmed = line.trim();
    const parts = trimmed.split(/\t|\s{2,}/);
    return (
      parts.length >= 2 &&
      trimmed !== '' &&
      !trimmed.startsWith('-') &&
      !trimmed.startsWith('*') &&
      !/^\d+\./.test(trimmed)
    );
  };

  while (i < lines.length) {
    if (isTableRow(lines[i])) {
      const tableRows = [];
      const startIndex = i;
      while (i < lines.length && isTableRow(lines[i])) {
        tableRows.push(
          lines[i]
            .trim()
            .split(/\t|\s{2,}/)
            .map((part) => part.trim())
        );
        i++;
      }

      if (tableRows.length >= 2) {
        const header = tableRows[0];
        const alignmentRow = header.map(() => '---');
        resultLines.push('| ' + header.join(' | ') + ' |');
        resultLines.push('| ' + alignmentRow.join(' | ') + ' |');
        for (let r = 1; r < tableRows.length; r++) {
          resultLines.push('| ' + tableRows[r].join(' | ') + ' |');
        }
      } else {
        resultLines.push(lines[startIndex]);
      }
    } else {
      resultLines.push(lines[i]);
      i++;
    }
  }

  return resultLines.join('\n');
}

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const renderedAnswer = message.content
    ? renderMarkdown(convertRawTableToMarkdown(message.content))
    : '...';
  return (
    <div className={`message-row ${isUser ? 'user' : 'bot'}`}>
      <div className={`avatar ${isUser ? 'user' : 'bot'}`}>{isUser ? 'U' : 'AI'}</div>
      <div className="content">
        {isUser ? (
          message.content
        ) : (
          <>
            {(message.thinking || message.loading) && (
              <ThinkingConsole thinking={message.thinking} loading={message.loading} />
            )}
            <div className="answer-text" dangerouslySetInnerHTML={{ __html: renderedAnswer }} />
          </>
        )}
      </div>
    </div>
  );
}