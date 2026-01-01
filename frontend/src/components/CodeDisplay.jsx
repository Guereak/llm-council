import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../contexts/ThemeContext';
import './CodeDisplay.css';

export default function CodeDisplay({ code, language, model, node, filename }) {
  const { isDarkMode } = useTheme();
  const [copied, setCopied] = useState(false);

  // Detect language from code if not provided
  const detectedLanguage = language || detectLanguage(code);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const handleDownload = () => {
    const extension = getFileExtension(detectedLanguage);
    const name = filename || `code.${extension}`;
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const theme = isDarkMode ? vscDarkPlus : vs;

  return (
    <div className="code-display">
      <div className="code-display-header">
        <div className="code-display-info">
          {model && (
            <span className="code-model">
              {model.split('/')[1] || model}
            </span>
          )}
          {node && (
            <span className="code-node">Node: {node}</span>
          )}
          {detectedLanguage && (
            <span className="code-language">{detectedLanguage}</span>
          )}
        </div>
        <div className="code-display-actions">
          <button
            className="code-action-btn"
            onClick={handleCopy}
            title="Copy to clipboard"
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
          <button
            className="code-action-btn"
            onClick={handleDownload}
            title="Download code"
          >
            💾 Download
          </button>
        </div>
      </div>
      <div className="code-display-content">
        <SyntaxHighlighter
          language={detectedLanguage}
          style={theme}
          customStyle={{
            margin: 0,
            borderRadius: '4px',
            fontSize: '14px',
          }}
          showLineNumbers
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

function detectLanguage(code) {
  // Simple language detection based on code patterns
  if (code.includes('def ') || code.includes('import ') || code.includes('from ')) {
    return 'python';
  }
  if (code.includes('function ') || code.includes('const ') || code.includes('let ') || code.includes('export ')) {
    return 'javascript';
  }
  if (code.includes('public class ') || code.includes('import java.')) {
    return 'java';
  }
  if (code.includes('#include') || code.includes('int main')) {
    return 'cpp';
  }
  if (code.includes('fn ') || code.includes('use ') || code.includes('pub ')) {
    return 'rust';
  }
  if (code.includes('package ') && code.includes('import ')) {
    return 'go';
  }
  return 'text';
}

function getFileExtension(language) {
  const extensions = {
    python: 'py',
    javascript: 'js',
    typescript: 'ts',
    java: 'java',
    cpp: 'cpp',
    c: 'c',
    rust: 'rs',
    go: 'go',
    html: 'html',
    css: 'css',
    json: 'json',
    yaml: 'yaml',
    shell: 'sh',
    bash: 'sh',
  };
  return extensions[language] || 'txt';
}

