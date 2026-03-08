import http from '@/api/http';

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const bytes = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) bytes[i] = rawData.charCodeAt(i);
  return bytes.buffer;
}

/**
 * Subscribe the current device to push notifications.
 * Permission must already be granted before calling this —
 * call Notification.requestPermission() directly from a click handler first.
 * Returns an error message string if something went wrong, or null on success.
 */
export async function registerPush(): Promise<string | null> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return 'Push not supported on this browser/device';
  }
  if (!('Notification' in window) || Notification.permission !== 'granted') {
    return 'Notification permission not granted';
  }

  // iOS requires the app to be running in standalone (home screen) mode
  const isStandalone =
    ('standalone' in navigator && (navigator as any).standalone === true) ||
    window.matchMedia('(display-mode: standalone)').matches;
  if (!isStandalone) {
    return 'Open the app from your home screen icon to enable push notifications';
  }

  try {
    const { data } = await http.get<{ public_key: string }>('/push/vapid-public-key');
    if (!data.public_key) return 'No VAPID public key returned by server';

    // Log current SW registration state for debugging
    const existing_reg = await navigator.serviceWorker.getRegistration('/');
    console.log('[push] SW installing:', existing_reg?.installing?.state ?? 'none');
    console.log('[push] SW waiting:', existing_reg?.waiting?.state ?? 'none');
    console.log('[push] SW active:', existing_reg?.active?.state ?? 'none');


    let registration: ServiceWorkerRegistration;
    try {
      registration = await Promise.race([
        navigator.serviceWorker.ready,
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('Service worker not ready after 8s')), 8000),
        ),
      ]);
    } catch (e: any) {
      return e?.message || 'Service worker not ready';
    }
    console.log('[push] SW ready, active state:', registration.active?.state);

    // Re-use an existing subscription if one already exists
    const existing = await registration.pushManager.getSubscription();
    if (existing) {
      console.log('[push] reusing existing subscription');
      const ej = existing.toJSON();
      await http.post('/push/subscribe', { endpoint: ej.endpoint, p256dh: ej.keys?.p256dh, auth: ej.keys?.auth });
      return null;
    }

    let subscription: PushSubscription;
    try {
      subscription = await Promise.race([
        registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(data.public_key),
        }),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('pushManager.subscribe() timed out after 8s')), 8000),
        ),
      ]);
    } catch (e: any) {
      const msg = e?.message || e?.name || String(e) || 'pushManager.subscribe() failed';
      console.error('[push] subscribe() error:', e);
      return msg;
    }

    const subJson = subscription.toJSON();
    console.log('[push] subscription created, endpoint:', subJson.endpoint?.slice(0, 50));

    if (!subJson.endpoint || !subJson.keys?.p256dh || !subJson.keys?.auth) {
      return 'Incomplete subscription data — missing endpoint or keys';
    }

    await http.post('/push/subscribe', {
      endpoint: subJson.endpoint,
      p256dh: subJson.keys.p256dh,
      auth: subJson.keys.auth,
    });

    console.log('[push] subscription saved to server');
    return null; // success
  } catch (e: any) {
    const msg = e?.message || String(e) || 'Unknown push error';
    console.error('[push] registerPush failed:', e);
    return msg;
  }
}
