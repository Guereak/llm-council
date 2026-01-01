import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import CodeInterface from './components/CodeInterface';
import HealthMonitor from './components/HealthMonitor';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [codeConversations, setCodeConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentView, setCurrentView] = useState('chat'); // 'chat', 'code', or 'health'

  // Load conversations on mount and when view changes
  useEffect(() => {
    if (currentView === 'chat') {
      loadConversations();
    } else if (currentView === 'code') {
      loadCodeConversations();
    }
  }, [currentView]);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      if (currentView === 'chat') {
        loadConversation(currentConversationId);
      } else if (currentView === 'code') {
        loadCodeConversation(currentConversationId);
      }
    }
  }, [currentConversationId, currentView]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadCodeConversations = async () => {
    try {
      const convs = await api.listCodeConversations();
      setCodeConversations(convs);
    } catch (error) {
      console.error('Failed to load code conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const loadCodeConversation = async (id) => {
    try {
      const conv = await api.getCodeConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load code conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleNewCodeConversation = async () => {
    try {
      const newConv = await api.createCodeConversation();
      setCodeConversations([
        { id: newConv.id, created_at: newConv.created_at, code_generation_count: 0 },
        ...codeConversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create code conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleViewChange = (view) => {
    setCurrentView(view);
    setCurrentConversationId(null);
    setCurrentConversation(null);
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage1 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage1_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage1 = event.data;
              lastMsg.loading.stage1 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage2_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage2 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage2_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage2 = event.data;
              lastMsg.metadata = event.metadata;
              lastMsg.loading.stage2 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage3_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage3 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage3_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage3 = event.data;
              lastMsg.loading.stage3 = false;
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
      // Stream complete, reload conversations list
      if (currentView === 'chat') {
        loadConversations();
      }
      setIsLoading(false);
      break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  const handleGenerateCode = async (specification, language, framework) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = {
        role: 'user',
        content: specification,
        specification,
        language,
        framework,
      };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...(prev?.messages || []), userMessage],
      }));

      // Create a partial assistant message
      const assistantMessage = {
        role: 'assistant',
        type: 'code_generation',
        code_generation: null,
        loading: { message: 'Generating code...' },
      };

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...(prev?.messages || []), assistantMessage],
      }));

      // Track iterations as they come in
      let iterations = [];
      let currentIteration = null;
      let finalCode = null;
      let finalTests = null;
      let tests = [];

      // Send code generation request with streaming
      await api.generateCodeStream(
        currentConversationId,
        specification,
        language,
        framework,
        2,
        (eventType, event) => {
          switch (eventType) {
            case 'code_generation_start':
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = { message: 'Generating initial code...' };
                return { ...prev, messages };
              });
              break;

            case 'code_generation_complete':
              iterations = [{
                iteration: 0,
                code_submissions: event.data || [],
                reviews: []
              }];
              currentIteration = iterations[0];
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = { message: 'Reviewing code...' };
                return { ...prev, messages };
              });
              break;

            case 'code_review_start':
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = {
                  message: `Reviewing code (Iteration ${event.iteration})...`,
                };
                return { ...prev, messages };
              });
              break;

            case 'code_review_complete':
              if (currentIteration) {
                currentIteration.reviews = event.data || [];
              }
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = {
                  message: `Refining code (Iteration ${event.iteration})...`,
                };
                return { ...prev, messages };
              });
              break;

            case 'code_refinement_start':
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = {
                  message: `Refining code (Iteration ${event.iteration})...`,
                };
                return { ...prev, messages };
              });
              break;

            case 'code_refinement_complete':
              if (event.iteration !== 'final') {
                iterations.push({
                  iteration: event.iteration,
                  code_submissions: event.data || [],
                  reviews: []
                });
                currentIteration = iterations[iterations.length - 1];
              }
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = { message: 'Reviewing final code...' };
                return { ...prev, messages };
              });
              break;

            case 'test_generation_start':
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = { message: 'Generating tests...' };
                return { ...prev, messages };
              });
              break;

            case 'test_generation_complete':
              tests = event.data || [];
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = { message: 'Synthesizing final code...' };
                return { ...prev, messages };
              });
              break;

            case 'code_synthesis_start':
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading = { message: 'Synthesizing final code...' };
                return { ...prev, messages };
              });
              break;

            case 'code_synthesis_complete':
              finalCode = event.data?.code || '';
              finalTests = event.data?.tests || '';
              setCurrentConversation((prev) => {
                const messages = [...(prev.messages)];
                const lastMsg = messages[messages.length - 1];
                lastMsg.code_generation = {
                  iterations: iterations,
                  final_code: finalCode,
                  final_tests: finalTests,
                  tests: tests,
                  metadata: {
                    language: language,
                    framework: framework,
                    total_iterations: iterations.length,
                  },
                };
                lastMsg.loading = null;
                return { ...prev, messages };
              });
              break;

            case 'title_complete':
              loadCodeConversations();
              break;

            case 'complete':
              loadCodeConversations();
              setIsLoading(false);
              break;

            case 'error':
              console.error('Code generation error:', event.message);
              setIsLoading(false);
              break;

            default:
              console.log('Unknown event type:', eventType);
          }
        }
      );
    } catch (error) {
      console.error('Failed to generate code:', error);
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        codeConversations={codeConversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onNewCodeConversation={handleNewCodeConversation}
        currentView={currentView}
        onViewChange={handleViewChange}
      />
      {currentView === 'chat' ? (
        <ChatInterface
          conversation={currentConversation}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      ) : currentView === 'code' ? (
        <CodeInterface
          conversation={currentConversation}
          onGenerateCode={handleGenerateCode}
          isLoading={isLoading}
        />
      ) : (
        <HealthMonitor />
      )}
    </div>
  );
}

export default App;
