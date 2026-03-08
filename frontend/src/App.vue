<script setup lang="ts">
  import MenubarAndDrawer from '@/snippets/MenubarAndDrawer.vue';
  import { useRoute } from 'vue-router';
  import ConfirmDialog from 'primevue/confirmdialog';
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
      // If push is already granted/denied, register silently without banner
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
  <div class="h-screen flex flex-col">
    <MenubarAndDrawer v-if="!route.meta.hideLayout"/>
    <ConfirmDialog />

    <!-- Push error message -->
    <Transition name="slide-down">
      <div v-if="pushError"
        class="flex items-center justify-between gap-3 px-4 py-3 bg-red-500 text-white text-sm shadow-md">
        <span>⚠️ {{ pushError }}</span>
        <button @click="pushError = null" class="opacity-70 hover:opacity-100 text-lg leading-none">✕</button>
      </div>
    </Transition>

    <!-- Push notification opt-in banner -->
    <Transition name="slide-down">
      <div v-if="showPushBanner"
        class="flex items-center justify-between gap-3 px-4 py-3 bg-primary text-white text-sm shadow-md">
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

    <div class="flex-1 flex">
      <router-view />
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
</style>
