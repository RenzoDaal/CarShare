/// <reference lib="webworker" />
declare const self: ServiceWorkerGlobalScope;

// This SW handles push notifications only — no precaching needed.

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event: PushEvent) => {
  const data = event.data?.json() ?? {};
  event.waitUntil(
    Promise.all([
      self.registration.showNotification(data.title || 'CarShare', {
        icon: '/pwa-192x192.png',
        badge: '/pwa-64x64.png',
      }),
      // Set the app icon badge (unread count from payload, or 1 as fallback)
      self.navigator.setAppBadge(data.badge ?? 1).catch(() => {}),
    ])
  );
});

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close();
  event.waitUntil(
    Promise.all([
      self.navigator.clearAppBadge().catch(() => {}),
      self.clients.openWindow('/'),
    ])
  );
});
