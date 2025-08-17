import { useMutation } from '@tanstack/react-query';
import { deployAgent } from '../api/agents';

export function useDeployAgent(agentId) {
  return useMutation({
    mutationFn: (channel) => deployAgent(agentId, channel)
  });
}
