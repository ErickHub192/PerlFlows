// src/api/credentials.ts

import { fetcher } from './fetcher';

export interface CredentialInput {
  provider: string;
  flavor?: string;
  client_id: string;
  client_secret: string;
  access_token?: string;
  refresh_token?: string;
  expires_at?: string;
  scopes?: string[];
  chat_id?: string;
}

export interface Credential extends CredentialInput {
  id: number;
  user_id: number;
  created_at: string;
  updated_at: string;
}


export const fetchCredentials = (
  params?: { chat_id?: string }
): Promise<Credential[]> => {
  const query = params?.chat_id
    ? `?chat_id=${encodeURIComponent(params.chat_id)}`
    : '';
  return fetcher(`/api/credentials${query}`, { method: 'GET' });
};


export const upsertCredential = (data: CredentialInput): Promise<Credential> =>
  fetcher('/api/credentials', { method: 'POST', body: data });

export const deleteCredential = (provider: string, flavor?: string, chat_id?: string): Promise<void> => {
  const params = new URLSearchParams();
  if (flavor) params.append('flavor', flavor);
  if (chat_id) params.append('chat_id', chat_id);
  const query = params.toString();
  return fetcher(`/api/credentials/${provider}${query ? `?${query}` : ''}`, { method: 'DELETE' });
};
