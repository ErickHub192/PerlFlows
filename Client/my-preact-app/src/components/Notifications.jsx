import useNotificationStore from '../stores/notificationStore';
import { useEffect } from 'preact/hooks';

export default function Notifications() {
  const notifications = useNotificationStore(s => s.notifications);
  const remove = useNotificationStore(s => s.remove);

  useEffect(() => {
    const timers = notifications.map(n =>
      setTimeout(() => remove(n.id), 3000)
    );
    return () => timers.forEach(t => clearTimeout(t));
  }, [notifications, remove]);

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 space-y-2 z-50">
      {notifications.map(n => (
        <div key={n.id} className="bg-gray-800 text-white px-3 py-2 rounded">
          {n.message}
        </div>
      ))}
    </div>
  );
}
