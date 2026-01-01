/**
 * API client for the LLM Council backend.
 */

const API_BASE = 'http://localhost:8001';

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  /**
   * Get cluster status.
   */
  async getClusterStatus() {
    const response = await fetch(`${API_BASE}/api/cluster/status`);
    if (!response.ok) {
      throw new Error('Failed to get cluster status');
    }
    return response.json();
  },

  /**
   * Run health check on all nodes.
   */
  async runHealthCheck() {
    const response = await fetch(`${API_BASE}/api/cluster/health-check`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to run health check');
    }
    return response.json();
  },

  /**
   * List all configured nodes.
   */
  async listNodes() {
    const response = await fetch(`${API_BASE}/api/cluster/nodes`);
    if (!response.ok) {
      throw new Error('Failed to list nodes');
    }
    return response.json();
  },

  /**
   * List all available models.
   */
  async listModels() {
    const response = await fetch(`${API_BASE}/api/cluster/models`);
    if (!response.ok) {
      throw new Error('Failed to list models');
    }
    return response.json();
  },

  // =============================================================================
  // CODE CONVERSATION METHODS
  // =============================================================================

  /**
   * List all code conversations.
   */
  async listCodeConversations() {
    const response = await fetch(`${API_BASE}/api/code/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list code conversations');
    }
    return response.json();
  },

  /**
   * Create a new code conversation.
   */
  async createCodeConversation() {
    const response = await fetch(`${API_BASE}/api/code/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create code conversation');
    }
    return response.json();
  },

  /**
   * Get a specific code conversation.
   */
  async getCodeConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/code/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get code conversation');
    }
    return response.json();
  },

  /**
   * Generate code with iterative refinement.
   */
  async generateCode(conversationId, specification, language, framework, maxIterations = 2) {
    const response = await fetch(
      `${API_BASE}/api/code/conversations/${conversationId}/generate`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          specification,
          language: language || null,
          framework: framework || null,
          max_iterations: maxIterations,
        }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to generate code');
    }
    return response.json();
  },

  /**
   * Generate code with streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} specification - Code specification
   * @param {string} language - Programming language (optional)
   * @param {string} framework - Framework/library (optional)
   * @param {number} maxIterations - Maximum refinement iterations
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async generateCodeStream(conversationId, specification, language, framework, maxIterations, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/code/conversations/${conversationId}/generate/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          specification,
          language: language || null,
          framework: framework || null,
          max_iterations: maxIterations,
        }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to generate code');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },
};
