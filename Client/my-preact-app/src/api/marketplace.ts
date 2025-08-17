import { fetcher } from './fetcher';

export function listTemplates() {
  return fetcher('/api/marketplace/templates', { method: 'GET' });
}

export function installTemplate(id: string) {
  return fetcher('/api/marketplace/install?template_id=' + id, { method: 'POST' });
}
