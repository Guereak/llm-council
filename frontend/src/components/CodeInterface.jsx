import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import CodeDisplay from './CodeDisplay';
import CodeReview from './CodeReview';
import CodeTests from './CodeTests';
import './CodeInterface.css';

// Move component outside to prevent recreation on every render
function CodeGenerationDisplay({ generation, selectedIteration, onSelectIteration }) {
  const iterations = generation.iterations || [];
  const finalCode = generation.final_code;
  const finalTests = generation.final_tests;
  const tests = generation.tests || [];
  const metadata = generation.metadata || {};

  return (
    <div className="code-generation">
      <div className="code-generation-header">
        <h3>Code Generation Results</h3>
        {metadata.total_iterations && (
          <span className="iteration-count">
            {metadata.total_iterations} iteration{metadata.total_iterations !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Iterations */}
      {iterations.length > 0 && (
        <div className="iterations-section">
          <h4 className="section-title">Iterations</h4>
          <div className="iterations-list">
            {iterations.map((iteration, idx) => (
              <IterationCard
                key={idx}
                iteration={iteration}
                iterationNum={idx}
                isSelected={selectedIteration === idx}
                onSelect={() => onSelectIteration(idx)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Final Code */}
      {finalCode && (
        <div className="final-code-section">
          <h4 className="section-title">Final Synthesized Code</h4>
          <CodeDisplay
            code={finalCode}
            language={metadata.language}
            filename={`final_code.${getExtension(metadata.language)}`}
          />
        </div>
      )}

      {/* Reviews */}
      {iterations.length > 0 && iterations[selectedIteration !== null ? selectedIteration : iterations.length - 1]?.reviews && (
        <div className="reviews-section">
          <h4 className="section-title">
            Reviews (Iteration {selectedIteration !== null ? selectedIteration : iterations.length - 1})
          </h4>
          <CodeReview
            reviews={iterations[selectedIteration !== null ? selectedIteration : iterations.length - 1].reviews}
          />
        </div>
      )}

      {/* Tests */}
      {(finalTests || tests.length > 0) && (
        <div className="tests-section">
          <CodeTests tests={tests} finalTests={finalTests} metadata={metadata} />
        </div>
      )}
    </div>
  );
}

function IterationCard({ iteration, iterationNum, isSelected, onSelect }) {
  const codeSubmissions = iteration.code_submissions || [];
  const reviews = iteration.reviews || [];

  return (
    <div
      className={`iteration-card ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
    >
      <div className="iteration-header">
        <span className="iteration-number">Iteration {iterationNum}</span>
        <span className="iteration-stats">
          {codeSubmissions.length} submission{codeSubmissions.length !== 1 ? 's' : ''}
          {reviews.length > 0 && ` • ${reviews.length} review${reviews.length !== 1 ? 's' : ''}`}
        </span>
      </div>
      {isSelected && codeSubmissions.length > 0 && (
        <div className="iteration-content">
          {codeSubmissions.map((submission, idx) => (
            <div key={idx} className="iteration-submission">
              <CodeDisplay
                code={submission.code}
                language={submission.language}
                model={submission.model}
                node={submission.node}
                filename={`iteration_${iterationNum}_${submission.model.replace('/', '_')}.${getExtension(submission.language)}`}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function getExtension(language) {
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

export default function CodeInterface({
  conversation,
  onGenerateCode,
  isLoading,
}) {
  const [specification, setSpecification] = useState('');
  const [language, setLanguage] = useState('');
  const [framework, setFramework] = useState('');
  const [selectedIteration, setSelectedIteration] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (specification.trim() && !isLoading) {
      onGenerateCode(specification, language || undefined, framework || undefined);
      setSpecification('');
      setLanguage('');
      setFramework('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="code-interface">
        <div className="empty-state">
          <h2>Welcome to Code Council</h2>
          <p>Create a new code conversation to generate code collaboratively</p>
        </div>
      </div>
    );
  }

  // Get code generations from conversation
  const codeGenerations = conversation.code_generations || [];
  const messages = conversation.messages || [];

  return (
    <div className="code-interface">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a code generation</h2>
            <p>Describe what code you want the council to generate</p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' && (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="specification-content">
                      <ReactMarkdown>{msg.content || msg.specification}</ReactMarkdown>
                      {msg.language && (
                        <div className="specification-meta">
                          <span className="meta-tag">Language: {msg.language}</span>
                          {msg.framework && (
                            <span className="meta-tag">Framework: {msg.framework}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
              {msg.type === 'code_generation' && (
                <div className="assistant-message">
                  <div className="message-label">Code Council</div>
                  
                  {msg.loading && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>{msg.loading.message || 'Generating code...'}</span>
                    </div>
                  )}

                  {msg.code_generation && (
                    <CodeGenerationDisplay
                      generation={msg.code_generation}
                      selectedIteration={selectedIteration}
                      onSelectIteration={setSelectedIteration}
                    />
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the code council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
          <div className="code-input-fields">
            <textarea
              className="message-input code-specification-input"
              placeholder="Describe the code you want to generate... (Enter to send, Shift+Enter for new line)"
              value={specification}
              onChange={(e) => setSpecification(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={6}
            />
            <div className="code-input-options">
              <input
                type="text"
                className="code-option-input"
                placeholder="Language (e.g., python, javascript)"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={isLoading}
              />
              <input
                type="text"
                className="code-option-input"
                placeholder="Framework (e.g., react, flask)"
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                disabled={isLoading}
              />
            </div>
          </div>
          <button
            type="submit"
            className="send-button"
            disabled={!specification.trim() || isLoading}
          >
            Generate Code
          </button>
      </form>
    </div>
  );
}
