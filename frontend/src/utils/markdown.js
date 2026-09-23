import { marked } from 'marked';

marked.setOptions({ gfm: true, breaks: true });

export function convertRawTableToMarkdown(text) {
  const lines = text.split('\n');
  const resultLines = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const parts = line.trim().split(/\t|\s{2,}/);
    const isTableLine = parts.length >= 2 && line.trim() !== '' &&
      !line.trim().startsWith('-') && !line.trim().startsWith('*') && !/^\d+\./.test(line.trim());

    if (!isTableLine) {
      resultLines.push(line);
      index += 1;
      continue;
    }

    const tableRows = [];
    while (index < lines.length) {
      const currentLine = lines[index];
      const currentParts = currentLine.trim().split(/\t|\s{2,}/);
      const validRow = currentParts.length >= 2 && currentLine.trim() !== '' &&
        !currentLine.trim().startsWith('-') && !currentLine.trim().startsWith('*') && !/^\d+\./.test(currentLine.trim());
      if (!validRow) break;
      tableRows.push(currentParts.map((part) => part.trim()));
      index += 1;
    }

    if (tableRows.length < 2) {
      resultLines.push(lines[index - tableRows.length]);
      continue;
    }

    resultLines.push(`| ${tableRows[0].join(' | ')} |`);
    resultLines.push(`| ${tableRows[0].map(() => '---').join(' | ')} |`);
    tableRows.slice(1).forEach((row) => resultLines.push(`| ${row.join(' | ')} |`));
  }

  return resultLines.join('\n');
}

export function renderMarkdown(text) {
  return marked.parse(convertRawTableToMarkdown(text || ''));
}
