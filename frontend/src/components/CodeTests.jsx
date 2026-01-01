import { useState } from 'react';
import CodeDisplay from './CodeDisplay';
import './CodeTests.css';

export default function CodeTests({ tests, finalTests, metadata }) {
  const [selectedTest, setSelectedTest] = useState(null);

  if (!tests || tests.length === 0) {
    return null;
  }

  // Detect test language from metadata or default to the code language
  const testLanguage = metadata?.language || 'javascript';
  const extension = getFileExtension(testLanguage);

  return (
    <div className="code-tests">
      <h3 className="code-tests-title">Generated Tests</h3>

      {finalTests && (
        <div className="final-tests-section">
          <h4 className="final-tests-title">Final Synthesized Tests</h4>
          <CodeDisplay
            code={finalTests}
            language={testLanguage}
            filename={`tests.${extension}`}
          />
        </div>
      )}

      <div className="test-submissions-section">
        <h4 className="test-submissions-title">Test Submissions from Council</h4>
        <div className="test-submissions-list">
          {tests.map((test, index) => (
            <div key={index} className="test-submission-card">
              <div className="test-submission-header">
                <span className="test-submission-model">
                  {test.model.split('/')[1] || test.model}
                </span>
                {test.node && (
                  <span className="test-submission-node">Node: {test.node}</span>
                )}
                <button
                  className="test-toggle-btn"
                  onClick={() => setSelectedTest(selectedTest === index ? null : index)}
                >
                  {selectedTest === index ? '▼ Hide' : '▶ Show'}
                </button>
              </div>
              {selectedTest === index && (
                <div className="test-submission-content">
                  <CodeDisplay
                    code={test.test_code}
                    language={testLanguage}
                    model={test.model}
                    node={test.node}
                    filename={`tests_${test.model.replace('/', '_')}.${extension}`}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
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
  };
  return extensions[language?.toLowerCase()] || 'txt';
}



