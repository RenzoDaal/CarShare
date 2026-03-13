<script setup lang="ts">
  import MenubarAndDrawer from '@/snippets/MenubarAndDrawer.vue';
  import { useRoute } from 'vue-router';
  import ConfirmDialog from 'primevue/confirmdialog';
  import Toast from 'primevue/toast';
  import { ref, watch } from 'vue';
  import { useAuthStore } from '@/stores/auth';
  import { registerPush } from '@/utils/push';
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
  const route = useRoute();
  const auth = useAuthStore();

  const showPushBanner = ref(false);

  watch(
    () => auth.isAuthenticated,
    (authenticated) => {
      if (!authenticated) return;
      if (!('Notification' in window)) return;
      if (Notification.permission === 'granted') {
        registerPush().then(err => { if (err) console.warn('[push]', err); });
      } else if (Notification.permission === 'default') {
        const dismissed = localStorage.getItem('push_banner_dismissed');
        if (!dismissed) showPushBanner.value = true;
      }
    },
    { immediate: true },
  );

  const pushError = ref<string | null>(null);

  async function enableNotifications() {
    showPushBanner.value = false;
    if (!('Notification' in window)) return;
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return;
    const error = await registerPush();
    if (error !== null) {
      pushError.value = error || t('app_push_error_fallback');
      setTimeout(() => { pushError.value = null; }, 10000);
    }
  }

  function dismissBanner() {
    showPushBanner.value = false;
    localStorage.setItem('push_banner_dismissed', '1');
  }
</script>


<template>
  <div class="h-screen flex overflow-hidden bg-surface-50 dark:bg-zinc-950">
    <MenubarAndDrawer v-if="!route.meta.hideLayout" />
    <ConfirmDialog />
    <Toast position="top-right" />

    <!-- Main content column -->
    <div
      class="flex-1 flex flex-col min-w-0"
      :class="{ 'lg:ml-60': !route.meta.hideLayout }"
    >
      <!-- Spacer for the fixed mobile top header (accounts for safe-area/notch) -->
      <div v-if="!route.meta.hideLayout" class="lg:hidden shrink-0"
        style="height: calc(3.5rem + env(safe-area-inset-top))" />

      <!-- Push error banner -->
      <Transition name="slide-down">
        <div v-if="pushError"
          class="flex items-center justify-between gap-3 px-4 py-3 bg-red-500 text-white text-sm shadow-md shrink-0">
          <span>⚠️ {{ pushError }}</span>
          <button @click="pushError = null" class="opacity-70 hover:opacity-100 text-lg leading-none">✕</button>
        </div>
      </Transition>

      <!-- Push notification opt-in banner -->
      <Transition name="slide-down">
        <div v-if="showPushBanner"
          class="flex items-center justify-between gap-3 px-4 py-3 bg-primary text-white text-sm shadow-md shrink-0">
          <span>🔔 {{ $t('app_push_banner') }}</span>
          <div class="flex items-center gap-2 shrink-0">
            <button @click="enableNotifications"
              class="font-semibold underline underline-offset-2 hover:opacity-80">
              {{ $t('app_push_enable') }}
            </button>
            <button @click="dismissBanner" class="opacity-70 hover:opacity-100 text-lg leading-none">✕</button>
          </div>
        </div>
      </Transition>

      <!-- Scrollable page area -->
      <div
        class="flex-1 overflow-y-auto relative"
        :class="{ 'pb-16 lg:pb-0': !route.meta.hideLayout }"
      >
        <router-view v-slot="{ Component }">
          <Transition name="page">
            <component :is="Component" />
          </Transition>
        </router-view>
      </div>
    </div>
  </div>
</template>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.25s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}

.page-enter-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-leave-active {
  transition: opacity 0.15s ease;
  position: absolute;
  width: 100%;
  pointer-events: none;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-leave-to {
  opacity: 0;
}
</style>
