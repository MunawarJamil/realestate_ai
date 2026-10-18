/**
 * Zero-dependency, safe Markdown parser for Assistant chat responses.
 * Protects against XSS by strictly escaping HTML before formatting.
 */

export function renderMarkdown(rawText: string): string {
  if (!rawText) return '';

  // 1. Escape HTML entities to prevent XSS
  let text = rawText
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  // 2. Code blocks (```code```)
  text = text.replace(/```([\s\S]*?)```/g, (_match, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // 3. Inline code (`code`)
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 4. Bold (**text** or __text__)
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>');

  // 5. Italic (*text* or _text_)
  text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  text = text.replace(/_([^_]+)_/g, '<em>$1</em>');

  // 6. Links [label](url)
  text = text.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );

  // 7. Bullet lists (- item or * item)
  const lines = text.split('\n');
  const formattedLines: string[] = [];
  let inList = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (!inList) {
        formattedLines.push('<ul>');
        inList = true;
      }
      formattedLines.push(`<li>${trimmed.substring(2)}</li>`);
    } else {
      if (inList) {
        formattedLines.push('</ul>');
        inList = false;
      }
      formattedLines.push(line);
    }
  }
  if (inList) {
    formattedLines.push('</ul>');
  }

  text = formattedLines.join('\n');

  // 8. Convert remaining newlines to <br/>
  text = text.replace(/\n\n+/g, '</p><p>').replace(/\n/g, '<br/>');

  return `<p>${text}</p>`.replace(/<p><\/p>/g, '');
}
