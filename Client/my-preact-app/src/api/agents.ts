import { fetcher } from './fetcher';

// Agent Management API
export interface Agent {
  agent_id: string;
  name: string;
  default_prompt: string;
  model: string;
  tools: string[];
  temperature: number;
  max_iterations: number;
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface AgentRun {
  run_id: string;
  agent_id: string;
  goal?: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  result?: any;
  error?: string;
  created_at: string;
  updated_at?: string;
}

export interface AgentStatistics {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  running_runs: number;
  queued_runs: number;
  success_rate: number;
  average_duration_minutes: number;
  last_run_date?: string;
}

export interface AgentAnalytics {
  agent_id: string;
  statistics: AgentStatistics;
  recent_runs: AgentRun[];
  daily_stats: Array<{
    date: string;
    total_runs: number;
    successful_runs: number;
    failed_runs: number;
    success_rate: number;
    average_duration_minutes: number;
  }>;
  period_start: string;
  period_end: string;
}

// API Functions
export async function listAgents(): Promise<Agent[]> {
  return fetcher('/api/ai_agents/');
}

export async function getAgent(agentId: string): Promise<Agent> {
  return fetcher(`/api/ai_agents/${agentId}`);
}

export async function getAgentModelConfig(agentId: string) {
  return fetcher(`/api/ai_agents/${agentId}/model-config`);
}

export async function listAvailableModels() {
  return fetcher('/api/ai_agents/models/available');
}

// Agent Runs API
export async function listAgentRuns(
  agentId: string, 
  page: number = 1, 
  pageSize: number = 20,
  status?: string
) {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString()
  });
  if (status) params.append('status', status);
  
  return fetcher(`/api/ai_agents/${agentId}/runs?${params.toString()}`);
}

export async function getAgentStatistics(agentId: string): Promise<AgentStatistics> {
  return fetcher(`/api/ai_agents/${agentId}/runs/statistics`);
}

export async function getAgentAnalytics(
  agentId: string, 
  days: number = 30,
  recentLimit: number = 10
): Promise<AgentAnalytics> {
  const params = new URLSearchParams({
    days: days.toString(),
    recent_limit: recentLimit.toString()
  });
  
  return fetcher(`/api/ai_agents/${agentId}/runs/analytics?${params.toString()}`);
}

export async function getRecentActivity(
  agentId: string,
  days: number = 7,
  limit: number = 10
): Promise<AgentRun[]> {
  const params = new URLSearchParams({
    days: days.toString(),
    limit: limit.toString()
  });
  
  return fetcher(`/api/ai_agents/${agentId}/runs/recent?${params.toString()}`);
}

export async function getSuccessTrend(agentId: string, days: number = 30) {
  const params = new URLSearchParams({
    days: days.toString()
  });
  
  return fetcher(`/api/ai_agents/${agentId}/runs/trend?${params.toString()}`);
}

export async function getRunDetails(runId: string): Promise<AgentRun> {
  return fetcher(`/api/ai_agents/runs/${runId}`);
}

// Agent Deployment
export function deployAgent(agentId: string, channel: string) {
  return fetcher(`/api/ai_agents/${agentId}/deploy`, {
    method: 'POST',
    body: { channel },
  });
}
