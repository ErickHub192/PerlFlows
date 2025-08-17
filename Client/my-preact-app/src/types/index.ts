// Core application types
export interface User {
  id: number;
  email: string;
  name?: string;
  role: 'user' | 'admin';
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// Chat related types
export interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  user_id: number;
  is_active: boolean;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  status?: 'sending' | 'sent' | 'failed' | 'received';
  data?: string; // JSON string with additional metadata
  error?: string;
  // UI-specific flags
  isSelectionFeedback?: boolean;
  skipBackend?: boolean;
}

export interface ChatHistories {
  [chatId: string]: ChatMessage[];
}

// Workflow related types
export interface WorkflowStep {
  id: string;
  node_id: string;
  action_id: string;
  node_name: string;
  action_name: string;
  params: Record<string, unknown>;
  params_meta?: Array<{
    name: string;
    type: string;
    required: boolean;
    description?: string;
  }>;
  default_auth?: string;
  uses_mcp?: boolean;
}

export interface OAuthRequirement {
  type: 'oauth';
  service_id: string;
  service_name: string;
  node_id: string;
  message: string;
  oauth_url: string;
}

export interface ServiceGroup {
  category: string;
  services: Array<{
    service_id: string;
    service_name: string;
    description: string;
  }>;
}

export interface SmartForm {
  form_id: string;
  title: string;
  description: string;
  fields: Array<{
    name: string;
    type: 'text' | 'number' | 'email' | 'select' | 'textarea';
    label: string;
    required: boolean;
    options?: string[];
    placeholder?: string;
    validation?: {
      pattern?: string;
      min?: number;
      max?: number;
    };
  }>;
}

export interface WorkflowResponse {
  reply: string;
  status: string;
  workflow_status?: string;
  workflow_action?: string;
  steps: WorkflowStep[];
  oauth_requirements: OAuthRequirement[];
  finalize: boolean;
  editable: boolean;
  enhanced_workflow: boolean;
  similar_services_found: boolean;
  service_groups: ServiceGroup[] | null;
  service_suggestions: string[] | null;
  smart_forms_required: boolean;
  smart_form: SmartForm | null;
  metadata: {
    confidence?: number;
    workflow_id?: string;
    execution_id?: string;
    [key: string]: unknown;
  };
}

// Store types
export interface ChatStore {
  chats: ChatSession[];
  activeChatId: string | null;
  chatHistories: ChatHistories;
  _intervals: Map<string, NodeJS.Timeout> | null;
  
  // Actions
  fetchSessions: () => Promise<ChatSession[]>;
  addChat: (title?: string) => Promise<string>;
  setActiveChat: (id: string) => void;
  updateChat: (id: string, updates: Partial<ChatSession>) => void;
  removeChat: (id: string) => Promise<void>;
  
  // Messages
  addMessage: (chatId: string, message: ChatMessage) => void;
  addAssistantMessage: (chatId: string, content: string, messageData?: unknown) => void;
  fetchMessages: (chatId: string) => Promise<ChatMessage[]>;
  sendMessage: (chatId: string, role: string, content: string, messageData?: unknown) => Promise<{ success: boolean }>;
  sendMessageWithServices: (chatId: string, message: string, selectedServices: string[], workflowType?: string) => Promise<WorkflowResponse>;
  
  // Utilities
  filterSystemMessages: (messages: ChatMessage[]) => ChatMessage[];
  cleanSystemMessages: () => void;
}

export interface ModeStore {
  mode: 'ai' | 'classic';
  setMode: (mode: 'ai' | 'classic') => void;
}

export interface NotificationStore {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: number;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// API types
export interface ApiError {
  status: number;
  message: string;
  detail?: Array<{
    msg: string;
    type: string;
    loc: string[];
  }>;
}

export interface FetchOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: Record<string, unknown>;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeout?: number;
}

// Component prop types
export interface ErrorBoundaryProps {
  children: preact.ComponentChildren;
  fallback?: preact.ComponentType<{ error: Error; retry: () => void }>;
}

export interface ChatViewProps {
  chatId?: string;
}

export interface AuthFlowProps {
  isOpen: boolean;
  onClose: () => void;
  serviceId: string;
  chatId: string;
  onSuccess: (authData: unknown) => void;
  onError: (error: Error) => void;
}

export interface OAuthRequirementHandlerProps {
  oauthRequirements: OAuthRequirement[];
  chatId: string;
  onAllCompleted: (completedProviders: string[], authData: unknown) => void;
  onError: (error: Error | string, requirement?: OAuthRequirement) => void;
}

// Utility types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// Environment types
export interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_AUTH_BASE_URL: string;
  readonly VITE_ENVIRONMENT: 'development' | 'staging' | 'production';
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_ANALYTICS_ID?: string;
}

export interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Window extensions for global state (to be eliminated)
declare global {
  interface Window {
    pendingServiceSelection?: {
      chatId: string;
      serviceGroups: ServiceGroup[];
      originalMessage: string;
    };
    smartFormContext?: {
      formSchema: SmartForm;
      isSmartForm: boolean;
      backendData: WorkflowResponse;
    };
    pendingFirstMessage?: string;
  }
}

export {};