<script setup lang="ts">
import { reactive, ref } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Checkbox from 'primevue/checkbox';
import Select from 'primevue/select';
import Message from 'primevue/message';
import { useAuthStore } from '@/stores/auth';
import { DEFAULT_NOTIFICATION_PREFS } from '@/stores/auth';
import type { NotificationPrefs, User } from '@/stores/auth';
import http from '@/api/http';
import { useI18n } from 'vue-i18n';
import { useToast } from 'primevue/usetoast';
import { applyColorTheme, getSavedTheme, applyCustomColor } from '@/utils/colorTheme';
import type { ColorThemeName } from '@/utils/colorTheme';

const { t, locale } = useI18n();
const toast = useToast();

const LANGUAGE_OPTIONS = [
  { label: 'Nederlands', value: 'nl' },
  { label: 'English', value: 'en' },
];

function setLocale(lang: string) {
  locale.value = lang;
  localStorage.setItem('locale', lang);
}

function getOffset(tz: string): string {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: tz,
    timeZoneName: 'shortOffset',
  }).formatToParts(new Date());
  const raw = parts.find(p => p.type === 'timeZoneName')?.value ?? 'GMT';
  return raw.replace('GMT', '') || '+0';
}

const TIMEZONE_ZONES: { value: string; cities: string }[] = [
  { value: 'Pacific/Midway',       cities: 'Midway Island, Samoa' },
  { value: 'Pacific/Honolulu',     cities: 'Hawaii' },
  { value: 'America/Anchorage',    cities: 'Alaska' },
  { value: 'America/Los_Angeles',  cities: 'Los Angeles, Seattle, Vancouver' },
  { value: 'America/Denver',       cities: 'Denver, Phoenix' },
  { value: 'America/Chicago',      cities: 'Chicago, Dallas, Mexico City' },
  { value: 'America/New_York',     cities: 'New York, Miami, Toronto' },
  { value: 'America/Halifax',      cities: 'Halifax, Atlantic Canada' },
  { value: 'America/Sao_Paulo',    cities: 'São Paulo, Brasília, Buenos Aires' },
  { value: 'Atlantic/Azores',      cities: 'Azores' },
  { value: 'UTC',                  cities: 'UTC / Reykjavik' },
  { value: 'Europe/London',        cities: 'London, Dublin, Lisbon' },
  { value: 'Europe/Amsterdam',     cities: 'Amsterdam, Paris, Brussels, Berlin, Rome, Madrid' },
  { value: 'Europe/Helsinki',      cities: 'Helsinki, Athens, Kyiv, Bucharest' },
  { value: 'Europe/Moscow',        cities: 'Moscow, Istanbul' },
  { value: 'Asia/Dubai',           cities: 'Dubai, Abu Dhabi' },
  { value: 'Asia/Karachi',         cities: 'Karachi, Islamabad' },
  { value: 'Asia/Kolkata',         cities: 'Mumbai, Delhi, Kolkata' },
  { value: 'Asia/Dhaka',           cities: 'Dhaka, Almaty' },
  { value: 'Asia/Bangkok',         cities: 'Bangkok, Jakarta, Hanoi' },
  { value: 'Asia/Shanghai',        cities: 'Beijing, Shanghai, Singapore, Hong Kong' },
  { value: 'Asia/Tokyo',           cities: 'Tokyo, Seoul, Osaka' },
  { value: 'Australia/Sydney',     cities: 'Sydney, Melbourne, Brisbane' },
  { value: 'Pacific/Auckland',     cities: 'Auckland, Wellington' },
];

const TIMEZONE_OPTIONS = TIMEZONE_ZONES.map(({ value, cities }) => ({
  value,
  label: `(${getOffset(value)}) ${cities}`,
}));

const auth = useAuthStore();

const userInitials = (() => {
  const name = auth.user?.full_name ?? '';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  return parts.slice(0, 2).map(p => p[0]).join('').toUpperCase();
})();

const profile = reactive({
  full_name: auth.user?.full_name ?? '',
  email: auth.user?.email ?? '',
  role_owner: auth.user?.role_owner ?? false,
  role_borrower: auth.user?.role_borrower ?? true,
  timezone: auth.user?.timezone ?? 'Europe/Amsterdam',
});
const profileSaving = ref(false);

async function saveProfile() {
  profileSaving.value = true;
  try {
    const { data } = await http.patch<User>('/users/me', {
      full_name: profile.full_name,
      email: profile.email,
      role_owner: profile.role_owner,
      role_borrower: profile.role_borrower,
      timezone: profile.timezone,
    });
    auth.updateUser(data);
    toast.add({ severity: 'success', summary: t('profile_saved_toast'), life: 3000 });
  } catch (err: any) {
    toast.add({ severity: 'error', summary: t('profile_error_save'), detail: err?.response?.data?.detail, life: 4000 });
  } finally {
    profileSaving.value = false;
  }
}

function parsePrefs(raw: string | null | undefined): NotificationPrefs {
  if (!raw) return structuredClone(DEFAULT_NOTIFICATION_PREFS);
  try {
    const parsed = JSON.parse(raw);
    const result = structuredClone(DEFAULT_NOTIFICATION_PREFS);
    for (const key of Object.keys(result) as (keyof NotificationPrefs)[]) {
      if (parsed[key]) {
        result[key].push = parsed[key].push ?? true;
        result[key].email = parsed[key].email ?? true;
      }
    }
    return result;
  } catch {
    return structuredClone(DEFAULT_NOTIFICATION_PREFS);
  }
}

const notifPrefs = reactive<NotificationPrefs>(parsePrefs(auth.user?.notification_prefs));
const notifSaving = ref(false);

const NOTIF_OWNER_TYPES: { key: keyof NotificationPrefs; labelKey: string; pushAlwaysOn?: boolean }[] = [
  { key: 'booking_request',    labelKey: 'profile_notif_booking_request' },
  { key: 'booking_reschedule', labelKey: 'profile_notif_booking_reschedule' },
  { key: 'booking_cancelled',  labelKey: 'profile_notif_booking_cancelled' },
  { key: 'co_owner_response',  labelKey: 'profile_notif_co_owner_response' },
  { key: 'booking_reminder',   labelKey: 'profile_notif_booking_reminder', pushAlwaysOn: true },
];

const NOTIF_BORROWER_TYPES: { key: keyof NotificationPrefs; labelKey: string }[] = [
  { key: 'booking_response', labelKey: 'profile_notif_booking_response' },
  { key: 'waitlist',         labelKey: 'profile_notif_waitlist' },
];

const NOTIF_GENERAL_TYPES: { key: keyof NotificationPrefs; labelKey: string }[] = [
  { key: 'co_owner_invite', labelKey: 'profile_notif_co_owner_invite' },
];

async function saveNotifPrefs() {
  notifSaving.value = true;
  try {
    const { data } = await http.patch<User>('/users/me', {
      notification_prefs: JSON.stringify(notifPrefs),
    });
    auth.updateUser(data);
    toast.add({ severity: 'success', summary: t('profile_notif_saved_toast'), life: 3000 });
  } catch (err: any) {
    toast.add({ severity: 'error', summary: t('profile_notif_error_save'), detail: err?.response?.data?.detail, life: 4000 });
  } finally {
    notifSaving.value = false;
  }
}

// --- Accent colour ---
const activeTheme = ref<ColorThemeName>(getSavedTheme());
const customColor = ref<string>(localStorage.getItem('customColor') ?? '#10b981');

const COLOR_SWATCHES: { name: ColorThemeName; bg: string; labelKey: string }[] = [
  { name: 'emerald', bg: '#10b981', labelKey: 'profile_accent_emerald' },
  { name: 'blue',    bg: '#3b82f6', labelKey: 'profile_accent_blue' },
  { name: 'violet',  bg: '#8b5cf6', labelKey: 'profile_accent_violet' },
  { name: 'orange',  bg: '#f97316', labelKey: 'profile_accent_orange' },
  { name: 'rose',    bg: '#f43f5e', labelKey: 'profile_accent_rose' },
];

function selectTheme(name: ColorThemeName) {
  activeTheme.value = name;
  if (name !== 'custom') applyColorTheme(name);
}

const passwords = reactive({ current: '', next: '', confirm: '' });
const passwordSaving = ref(false);
const passwordError = ref<string | null>(null);

async function changePassword() {
  passwordError.value = null;
  if (passwords.next !== passwords.confirm) {
    passwordError.value = t('profile_password_error_no_match');
    return;
  }
  if (passwords.next.length < 6) {
    passwordError.value = t('profile_password_error_min_length');
    return;
  }
  passwordSaving.value = true;
  try {
    await http.post('/users/me/change-password', {
      current_password: passwords.current,
      new_password: passwords.next,
    });
    passwords.current = '';
    passwords.next = '';
    passwords.confirm = '';
    toast.add({ severity: 'success', summary: t('profile_password_changed_toast'), life: 3000 });
  } catch (err: any) {
    toast.add({ severity: 'error', summary: t('profile_password_error_save'), detail: err?.response?.data?.detail, life: 4000 });
  } finally {
    passwordSaving.value = false;
  }
}
</script>

<template>
  <div class="p-4 flex flex-col gap-5 max-w-2xl mx-auto w-full">

    <!-- Profile header -->
    <div class="flex items-center gap-4">
      <div class="w-16 h-16 rounded-2xl bg-primary/15 text-primary flex items-center justify-center text-2xl font-bold shrink-0">
        {{ userInitials }}
      </div>
      <div>
        <h1 class="text-2xl font-bold tracking-tight">{{ auth.user?.full_name }}</h1>
        <p class="text-sm text-surface-400 mt-0.5">{{ auth.user?.email }}</p>
      </div>
    </div>

    <!-- ── Account details ── -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
            <i class="pi pi-user text-primary text-xs" />
          </div>
          <span>{{ $t('profile_account_details') }}</span>
        </div>
      </template>
      <template #content>
        <div class="flex flex-col gap-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-sm font-medium">{{ $t('profile_full_name_label') }}</label>
              <InputText v-model="profile.full_name" class="w-full" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-sm font-medium">{{ $t('profile_email_label') }}</label>
              <InputText v-model="profile.email" class="w-full" />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-sm font-medium">{{ $t('profile_timezone_label') }}</label>
              <Select v-model="profile.timezone" :options="TIMEZONE_OPTIONS" optionLabel="label" optionValue="value" fluid />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-sm font-medium">{{ $t('profile_language_label') }}</label>
              <Select :modelValue="locale" :options="LANGUAGE_OPTIONS" optionLabel="label" optionValue="value" fluid
                @update:modelValue="setLocale" />
            </div>
          </div>

          <div class="flex flex-col gap-2">
            <span class="text-sm font-medium">{{ $t('profile_roles_label') }}</span>
            <div class="flex gap-3">
              <label
                class="flex-1 flex items-center gap-2.5 p-3 rounded-xl border-2 cursor-pointer transition-all"
                :class="profile.role_owner
                  ? 'border-primary bg-primary/5 dark:bg-primary/10'
                  : 'border-surface-200 dark:border-zinc-700 hover:border-surface-300'"
              >
                <Checkbox v-model="profile.role_owner" :binary="true" inputId="profile_role_owner" />
                <p class="text-sm font-medium">{{ $t('profile_role_owner_label') }}</p>
              </label>
              <label
                class="flex-1 flex items-center gap-2.5 p-3 rounded-xl border-2 cursor-pointer transition-all"
                :class="profile.role_borrower
                  ? 'border-primary bg-primary/5 dark:bg-primary/10'
                  : 'border-surface-200 dark:border-zinc-700 hover:border-surface-300'"
              >
                <Checkbox v-model="profile.role_borrower" :binary="true" inputId="profile_role_borrower" />
                <p class="text-sm font-medium">{{ $t('profile_role_borrower_label') }}</p>
              </label>
            </div>
          </div>

          <div class="flex justify-end">
            <Button :label="$t('profile_save')" icon="pi pi-check" :loading="profileSaving" @click="saveProfile" />
          </div>
        </div>
      </template>
    </Card>

    <!-- ── Accent colour ── -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
            <i class="pi pi-palette text-primary text-xs" />
          </div>
          <span>{{ $t('profile_accent_color_title') }}</span>
        </div>
      </template>
      <template #content>
        <p class="text-sm text-surface-500 mb-4">{{ $t('profile_accent_color_hint') }}</p>
        <div class="flex gap-3 flex-wrap">
          <button
            v-for="swatch in COLOR_SWATCHES"
            :key="swatch.name"
            type="button"
            :title="$t(swatch.labelKey)"
            class="w-9 h-9 rounded-full transition-all duration-200 focus:outline-none"
            :class="activeTheme === swatch.name
              ? 'ring-2 ring-offset-2 ring-primary scale-110'
              : 'hover:scale-110 opacity-80 hover:opacity-100'"
            :style="{ backgroundColor: swatch.bg }"
            @click="selectTheme(swatch.name)"
          />
          <!-- Custom colour picker -->
          <label
            class="relative w-9 h-9 rounded-full cursor-pointer transition-all duration-200 focus-within:outline-none overflow-hidden"
            :class="activeTheme === 'custom'
              ? 'ring-2 ring-offset-2 ring-primary scale-110'
              : 'hover:scale-110 opacity-80 hover:opacity-100'"
            title="Custom colour"
          >
            <input
              type="color"
              class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              :value="customColor"
              @input="(e) => {
                const hex = (e.target as HTMLInputElement).value;
                customColor = hex;
                activeTheme = 'custom';
                applyCustomColor(hex);
              }"
            />
            <div class="w-full h-full rounded-full flex items-center justify-center"
              :style="{ backgroundColor: activeTheme === 'custom' ? customColor : '#94a3b8' }">
              <i class="pi pi-pencil text-white text-[10px]" />
            </div>
          </label>
        </div>
        <p class="text-xs text-surface-400 mt-3">{{ $t(COLOR_SWATCHES.find(s => s.name === activeTheme)?.labelKey ?? '') }}</p>
      </template>
    </Card>

    <!-- ── Notification preferences ── -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
            <i class="pi pi-bell text-primary text-xs" />
          </div>
          <span>{{ $t('profile_notifications_title') }}</span>
        </div>
      </template>
      <template #content>
        <div class="flex flex-col gap-5">

          <!-- Owner section -->
          <template v-if="profile.role_owner">
            <p class="text-xs font-semibold uppercase tracking-widest text-surface-400">{{ $t('profile_as_owner') }}</p>
            <div class="rounded-xl border border-surface-200 dark:border-zinc-700 overflow-hidden">
              <div class="grid grid-cols-[1fr_auto_auto] gap-x-6 items-center px-4 py-2.5 bg-surface-50 dark:bg-zinc-800">
                <span class="text-xs font-medium text-surface-400 uppercase tracking-wide">{{ $t('profile_notif_type_col') }}</span>
                <span class="text-xs font-medium text-surface-400 uppercase tracking-wide text-center">{{ $t('profile_notif_inapp_col') }}</span>
                <span class="text-xs font-medium text-surface-400 uppercase tracking-wide text-center">{{ $t('profile_notif_email_col') }}</span>
              </div>
              <div v-for="(type, idx) in NOTIF_OWNER_TYPES" :key="type.key"
                class="grid grid-cols-[1fr_auto_auto] gap-x-6 items-center px-4 py-3"
                :class="idx > 0 ? 'border-t border-surface-100 dark:border-zinc-800' : ''">
                <span class="text-sm">{{ $t(type.labelKey) }}</span>
                <div class="flex justify-center">
                  <i v-if="type.pushAlwaysOn" class="pi pi-check text-primary text-sm" :title="$t('profile_notif_push_always_on')" />
                  <Checkbox v-else v-model="notifPrefs[type.key].push" :binary="true" />
                </div>
                <div class="flex justify-center">
                  <Checkbox v-model="notifPrefs[type.key].email" :binary="true" />
                </div>
              </div>
            </div>
          </template>

          <!-- Borrower section -->
          <template v-if="profile.role_borrower">
            <p class="text-xs font-semibold uppercase tracking-widest text-surface-400">{{ $t('profile_as_borrower') }}</p>
            <div class="rounded-xl border border-surface-200 dark:border-zinc-700 overflow-hidden">
              <div class="grid grid-cols-[1fr_auto_auto] gap-x-6 items-center px-4 py-2.5 bg-surface-50 dark:bg-zinc-800">
                <span class="text-xs font-medium text-surface-400 uppercase tracking-wide">{{ $t('profile_notif_type_col') }}</span>
                <span class="text-xs font-medium text-surface-400 uppercase tracking-wide text-center">{{ $t('profile_notif_inapp_col') }}</span>
                <span class="text-xs font-medium text-surface-400 uppercase tracking-wide text-center">{{ $t('profile_notif_email_col') }}</span>
              </div>
              <div v-for="(type, idx) in NOTIF_BORROWER_TYPES" :key="type.key"
                class="grid grid-cols-[1fr_auto_auto] gap-x-6 items-center px-4 py-3"
                :class="idx > 0 ? 'border-t border-surface-100 dark:border-zinc-800' : ''">
                <span class="text-sm">{{ $t(type.labelKey) }}</span>
                <div class="flex justify-center">
                  <Checkbox v-model="notifPrefs[type.key].push" :binary="true" />
                </div>
                <div class="flex justify-center">
                  <Checkbox v-model="notifPrefs[type.key].email" :binary="true" />
                </div>
              </div>
            </div>
          </template>

          <!-- General section -->
          <p class="text-xs font-semibold uppercase tracking-widest text-surface-400">{{ $t('profile_as_general') }}</p>
          <div class="rounded-xl border border-surface-200 dark:border-zinc-700 overflow-hidden">
            <div class="grid grid-cols-[1fr_auto_auto] gap-x-6 items-center px-4 py-2.5 bg-surface-50 dark:bg-zinc-800">
              <span class="text-xs font-medium text-surface-400 uppercase tracking-wide">{{ $t('profile_notif_type_col') }}</span>
              <span class="text-xs font-medium text-surface-400 uppercase tracking-wide text-center">{{ $t('profile_notif_inapp_col') }}</span>
              <span class="text-xs font-medium text-surface-400 uppercase tracking-wide text-center">{{ $t('profile_notif_email_col') }}</span>
            </div>
            <div v-for="(type, idx) in NOTIF_GENERAL_TYPES" :key="type.key"
              class="grid grid-cols-[1fr_auto_auto] gap-x-6 items-center px-4 py-3"
              :class="idx > 0 ? 'border-t border-surface-100 dark:border-zinc-800' : ''">
              <span class="text-sm">{{ $t(type.labelKey) }}</span>
              <div class="flex justify-center">
                <Checkbox v-model="notifPrefs[type.key].push" :binary="true" />
              </div>
              <div class="flex justify-center">
                <Checkbox v-model="notifPrefs[type.key].email" :binary="true" />
              </div>
            </div>
          </div>

          <div class="flex justify-end">
            <Button :label="$t('profile_notif_save')" icon="pi pi-check" :loading="notifSaving" @click="saveNotifPrefs" />
          </div>
        </div>
      </template>
    </Card>

    <!-- ── Change password ── -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
            <i class="pi pi-lock text-primary text-xs" />
          </div>
          <span>{{ $t('profile_change_password_title') }}</span>
        </div>
      </template>
      <template #content>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-medium">{{ $t('profile_current_password') }}</label>
            <Password v-model="passwords.current" :feedback="false" toggleMask class="w-full" inputClass="w-full" />
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-sm font-medium">{{ $t('profile_new_password') }}</label>
              <Password v-model="passwords.next" :feedback="false" toggleMask class="w-full" inputClass="w-full" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-sm font-medium">{{ $t('profile_confirm_new_password') }}</label>
              <Password v-model="passwords.confirm" :feedback="false" toggleMask class="w-full" inputClass="w-full" />
            </div>
          </div>

          <Message v-if="passwordError" severity="error" :closable="false">{{ passwordError }}</Message>

          <div class="flex justify-end">
            <Button :label="$t('profile_change_password_button')" icon="pi pi-lock" :loading="passwordSaving"
              @click="changePassword" />
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>
