import { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  codeConversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onNewCodeConversation,
  currentView,
  onViewChange,
}) {
  const { isDarkMode, toggleDarkMode } = useTheme();

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>LLM Council</h1>
        <div className="theme-toggle-container">
          <button className="theme-toggle" onClick={toggleDarkMode}>
            {isDarkMode ? '☀️ Light' : '🌙 Dark'}
          </button>
        </div>
      </div>

      <div className="sidebar-nav">
        <button
          className={`nav-btn ${currentView === 'chat' ? 'active' : ''}`}
          onClick={() => onViewChange('chat')}
        >
          💬 Chat
        </button>
        <button
          className={`nav-btn ${currentView === 'code' ? 'active' : ''}`}
          onClick={() => onViewChange('code')}
        >
          💻 Code
        </button>
        <button
          className={`nav-btn ${currentView === 'health' ? 'active' : ''}`}
          onClick={() => onViewChange('health')}
        >
          ❤️ Health Monitor
        </button>
      </div>

      {currentView === 'chat' && (
        <>
          <button className="new-conversation-btn" onClick={onNewConversation}>
            + New Conversation
          </button>
          <div className="conversation-list">
            {conversations.length === 0 ? (
              <div className="no-conversations">No conversations yet</div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item ${
                    conv.id === currentConversationId ? 'active' : ''
                  }`}
                  onClick={() => onSelectConversation(conv.id)}
                >
                  <div className="conversation-title">
                    {conv.title || 'New Conversation'}
                  </div>
                  <div className="conversation-meta">
                    {conv.message_count} messages
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {currentView === 'code' && (
        <>
          <button className="new-conversation-btn" onClick={onNewCodeConversation}>
            + New Code Conversation
          </button>
          <div className="conversation-list">
            {(!codeConversations || codeConversations.length === 0) ? (
              <div className="no-conversations">No code conversations yet</div>
            ) : (
              codeConversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item ${
                    conv.id === currentConversationId ? 'active' : ''
                  }`}
                  onClick={() => onSelectConversation(conv.id)}
                >
                  <div className="conversation-title">
                    {conv.title || 'New Code Conversation'}
                  </div>
                  <div className="conversation-meta">
                    {conv.code_generation_count || 0} generation{conv.code_generation_count !== 1 ? 's' : ''}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
