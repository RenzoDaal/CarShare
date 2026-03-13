/**
 * Trigger a haptic vibration on supported mobile devices.
 * Silently ignored on desktop or unsupported browsers.
 */
export function haptic(pattern: number | number[] = 50): void {
  if ('vibrate' in navigator) {
    navigator.vibrate(pattern);
  }
}
