import { useQuery, useMutation } from '@tanstack/react-query';
import { listTemplates, installTemplate } from '../api/marketplace';
import useNotificationStore from '../stores/notificationStore';

export function useTemplates() {
  return useQuery({
    queryKey: ['marketplace', 'templates'],
    queryFn: listTemplates
  });
}

export function useInstallTemplate() {
  const notify = useNotificationStore(state => state.add);
  return useMutation({
    mutationFn: (id) => installTemplate(id),
    onSuccess: () => {
      notify({ type: 'success', message: 'Plantilla instalada' });
    },
  });
}
