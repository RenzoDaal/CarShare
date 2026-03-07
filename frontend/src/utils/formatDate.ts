import { useAuthStore } from '@/stores/auth';

function getUserTimezone(): string {
  return useAuthStore().user?.timezone ?? 'Europe/Amsterdam';
}

function toUtcDate(value: string | Date): Date {
  if (value instanceof Date) return value;
  const normalized = value.endsWith('Z') || value.includes('+') ? value : value + 'Z';
  return new Date(normalized);
}

export function formatDateTime(value: string | Date): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: getUserTimezone(),
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(toUtcDate(value));
}

export function formatDateOnly(value: string | Date): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: getUserTimezone(),
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(toUtcDate(value));
}
