import { vi } from 'vitest';
import type { 
  ChatSession, 
  ChatMessage, 
  WorkflowResponse, 
  OAuthRequirement 
} from '@/types';

// Mock data factories
export const createMockChatSession = (overrides: Partial<ChatSession> = {}): ChatSession => ({
  session_id: 'test-session-1',
  title: 'Test Chat',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  user_id: 1,
  is_active: true,
  ...overrides,
});

export const createMockChatMessage = (overrides: Partial<ChatMessage> = {}): ChatMessage => ({
  id: 'test-message-1',
  role: 'user',
  content: 'Test message',
  timestamp: '2024-01-01T00:00:00Z',
  status: 'sent',
  ...overrides,
});

export const createMockWorkflowResponse = (overrides: Partial<WorkflowResponse> = {}): WorkflowResponse => ({
  reply: 'Test workflow response',
  status: 'ready',
  steps: [],
  oauth_requirements: [],
  finalize: false,
  editable: true,
  enhanced_workflow: false,
  similar_services_found: false,
  service_groups: null,
  service_suggestions: null,
  smart_forms_required: false,
  smart_form: null,
  metadata: {},
  ...overrides,
});

export const createMockOAuthRequirement = (overrides: Partial<OAuthRequirement> = {}): OAuthRequirement => ({
  type: 'oauth',
  service_id: 'google',
  service_name: 'Google',
  node_id: 'test-node-1',
  message: 'Authentication required',
  oauth_url: '/auth/google',
  ...overrides,
});

// API response mocks
export const mockApiResponses = {
  // Chat endpoints
  chatSessions: {
    success: [createMockChatSession()],
    error: { status: 500, message: 'Internal server error' }
  },
  
  chatMessages: {
    success: [createMockChatMessage()],
    error: { status: 404, message: 'Chat not found' }
  },
  
  sendMessage: {
    success: createMockWorkflowResponse(),
    error: { status: 400, message: 'Invalid message' }
  },
  
  // Auth endpoints
  login: {
    success: { 
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
      user: { id: 1, email: 'test@example.com', role: 'user' }
    },
    error: { status: 401, message: 'Invalid credentials' }
  },
  
  refresh: {
    success: { access_token: 'new-mock-token' },
    error: { status: 401, message: 'Invalid refresh token' }
  }
};

// Fetch mock implementation
export const createMockFetch = (responses: Record<string, any> = {}) => {
  return vi.fn().mockImplementation((url: string, options?: RequestInit) => {
    const method = options?.method || 'GET';
    const key = `${method}:${url}`;
    
    const response = responses[key] || responses[url];
    
    if (!response) {
      return Promise.reject(new Error(`No mock response for ${key}`));
    }
    
    if (response.error) {
      return Promise.resolve({
        ok: false,
        status: response.error.status,
        json: () => Promise.resolve(response.error),
      });
    }
    
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(response.success || response),
    });
  });
};

// Store mocks
export const createMockChatStore = () => ({
  chats: [createMockChatSession()],
  activeChatId: 'test-session-1',
  chatHistories: {
    'test-session-1': [createMockChatMessage()]
  },
  fetchSessions: vi.fn().mockResolvedValue([createMockChatSession()]),
  addChat: vi.fn().mockResolvedValue('new-session-id'),
  setActiveChat: vi.fn(),
  updateChat: vi.fn(),
  removeChat: vi.fn().mockResolvedValue(undefined),
  addMessage: vi.fn(),
  addAssistantMessage: vi.fn(),
  fetchMessages: vi.fn().mockResolvedValue([createMockChatMessage()]),
  sendMessage: vi.fn().mockResolvedValue({ success: true }),
  sendMessageWithServices: vi.fn().mockResolvedValue(createMockWorkflowResponse()),
  filterSystemMessages: vi.fn().mockImplementation((messages) => messages),
  cleanSystemMessages: vi.fn(),
});

export const createMockAuthStore = () => ({
  user: { id: 1, email: 'test@example.com', role: 'user' as const },
  token: 'mock-token',
  refreshToken: 'mock-refresh-token',
  isAuthenticated: true,
  isLoading: false,
  error: null,
  login: vi.fn().mockResolvedValue({ success: true }),
  logout: vi.fn(),
  refresh: vi.fn().mockResolvedValue('new-token'),
  checkAuth: vi.fn().mockResolvedValue(true),
});

// Component test utilities
export const mockWindowLocation = (url: string) => {
  const location = new URL(url);
  Object.defineProperty(window, 'location', {
    value: {
      href: location.href,
      pathname: location.pathname,
      search: location.search,
      hash: location.hash,
      assign: vi.fn(),
      replace: vi.fn(),
      reload: vi.fn(),
    },
    writable: true,
  });
};

export const mockRouter = () => ({
  route: vi.fn(),
  getCurrentUrl: vi.fn().mockReturnValue('/'),
});

// Error boundary test utilities
export const ThrowError = ({ error }: { error: Error }) => {
  throw error;
};

export const TestErrorComponent = () => {
  throw new Error('Test error');
};

// Async utilities for testing
export const waitForPromises = () => new Promise(setImmediate);

export const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));