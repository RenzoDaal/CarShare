<script setup lang="ts">
  import Button from 'primevue/button';
  import Drawer from 'primevue/drawer';
  import Popover from 'primevue/popover';
  import Logo from '@/assets/logo.svg';

  import { ref, computed, onMounted, onUnmounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { useAuthStore } from '../stores/auth';
  import http from '@/api/http';
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  type Notification = {
    id: number;
    message: string;
    is_read: boolean;
    created_at: string;
    booking_id?: number | null;
  };

  const auth = useAuthStore();
  const router = useRouter();
  const route = useRoute();

  const userInitials = computed(() => {
    const name = auth.user?.full_name ?? '';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return '?';
    return parts.slice(0, 2).map(p => p[0]).join('').toUpperCase();
  });

  const logout = () => {
    auth.logout();
    drawerVisible.value = false;
    router.push({ name: 'login' });
  };

  const isDark = ref(document.documentElement.classList.contains('dark'));

  const toggleDarkMode = () => {
    isDark.value = !isDark.value;
    document.documentElement.classList.toggle('dark', isDark.value);
    localStorage.setItem('darkMode', String(isDark.value));
  };

  const drawerVisible = ref(false);
  const isCarOwner = computed(() => auth.user?.role_owner ?? false);
  const isCarBorrower = computed(() => auth.user?.role_borrower ?? false);
  const isAdmin = computed(() => auth.user?.is_admin ?? false);

  const pendingBookingsCount = ref(0);

  const notifPopover = ref();
  const notifications = ref<Notification[]>([]);
  const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length);

  async function loadNotifications() {
    try {
      const { data } = await http.get<Notification[]>('/notifications');
      notifications.value = data;
      const count = data.filter((n: Notification) => !n.is_read).length;
      if ('setAppBadge' in navigator) {
        count > 0
          ? navigator.setAppBadge(count).catch(() => {})
          : navigator.clearAppBadge().catch(() => {});
      }
    } catch {
      // silently ignore
    }
  }

  async function toggleNotifPopover(event: Event) {
    notifPopover.value.toggle(event);
    if (unreadCount.value > 0) {
      await http.post('/notifications/read-all');
      notifications.value = notifications.value.map(n => ({ ...n, is_read: true }));
      if ('clearAppBadge' in navigator) navigator.clearAppBadge().catch(() => {});
    }
  }

  async function clearAllNotifications() {
    try {
      await http.delete('/notifications');
      notifications.value = [];
      if ('clearAppBadge' in navigator) navigator.clearAppBadge().catch(() => {});
      notifPopover.value.hide();
    } catch {
      // silently ignore
    }
  }

  function handleNotifClick(notif: Notification) {
    if (notif.booking_id) {
      router.push({ name: 'booking-detail', params: { id: notif.booking_id } });
      notifPopover.value.hide();
    }
  }

  let notifInterval: ReturnType<typeof setInterval> | null = null;

  onMounted(async () => {
    if (isCarOwner.value) {
      try {
        const { data } = await http.get<{ status: string }[]>('/bookings/owner');
        pendingBookingsCount.value = data.filter(b => b.status === 'pending').length;
      } catch {
        // silently ignore
      }
    }
    loadNotifications();
    notifInterval = setInterval(loadNotifications, 30_000);
  });

  onUnmounted(() => {
    if (notifInterval) clearInterval(notifInterval);
  });

  type NavItem = {
    label: string;
    icon: string;
    routeName: string;
    badge?: number;
  };

  type NavSection = {
    label?: string;
    items: NavItem[];
  };

  const navSections = computed((): NavSection[] => {
    const sections: NavSection[] = [
      {
        items: [
          { label: t('nav_dashboard'), icon: 'pi pi-home', routeName: 'home' },
          { label: t('nav_my_profile'), icon: 'pi pi-user', routeName: 'profile' },
        ],
      },
    ];

    if (isCarOwner.value) {
      sections.push({
        label: t('nav_owner'),
        items: [
          { label: t('nav_manage_cars'), icon: 'pi pi-car', routeName: 'manage cars' },
          {
            label: t('nav_appointments'),
            icon: 'pi pi-inbox',
            routeName: 'ownerappointments',
            badge: pendingBookingsCount.value > 0 ? pendingBookingsCount.value : undefined,
          },
        ],
      });
    }

    if (isCarBorrower.value) {
      sections.push({
        label: t('nav_borrower'),
        items: [
          { label: t('nav_reserve'), icon: 'pi pi-calendar-plus', routeName: 'reserve car' },
          { label: t('nav_my_appointments'), icon: 'pi pi-list', routeName: 'borrowerappointments' },
          { label: t('nav_availability'), icon: 'pi pi-calendar-clock', routeName: 'availability' },
        ],
      });
    }

    if (isAdmin.value) {
      sections.push({
        label: t('nav_admin'),
        items: [
          { label: t('nav_user_management'), icon: 'pi pi-users', routeName: 'admin' },
        ],
      });
    }

    return sections;
  });

  function navigate(routeName: string) {
    router.push({ name: routeName });
    drawerVisible.value = false;
  }

  function isActive(routeName: string) {
    return route.name === routeName;
  }
</script>


<template>
  <!-- Shared notification popover (triggered from both desktop & mobile buttons) -->
  <Popover ref="notifPopover">
    <div class="w-[min(320px,85vw)] flex flex-col">
      <div class="px-1 pb-2 flex items-center justify-between">
        <span class="font-semibold text-sm">{{ $t('nav_notifications') }}</span>
        <span v-if="unreadCount > 0" class="text-xs text-surface-400">{{ unreadCount }} unread</span>
      </div>
      <div v-if="notifications.length === 0" class="text-sm text-surface-500 py-6 text-center">
        <i class="pi pi-bell-slash text-2xl block mb-2 text-surface-300" />
        {{ $t('nav_no_notifications') }}
      </div>
      <ul v-else class="flex flex-col gap-0.5 max-h-72 overflow-y-auto">
        <li
          v-for="notif in notifications"
          :key="notif.id"
          class="text-sm px-3 py-2.5 rounded-xl transition-colors"
          :class="[
            notif.is_read ? 'text-surface-500' : 'font-medium bg-surface-100 dark:bg-zinc-800',
            notif.booking_id ? 'cursor-pointer hover:bg-surface-200 dark:hover:bg-zinc-700' : ''
          ]"
          @click="handleNotifClick(notif)"
        >
          {{ notif.message }}
        </li>
      </ul>
      <div v-if="notifications.length > 0" class="pt-2 mt-1 border-t border-surface-100 dark:border-zinc-700">
        <Button :label="$t('nav_clear_notifications')" icon="pi pi-times" text size="small" severity="secondary"
          class="w-full" @click="clearAllNotifications" />
      </div>
    </div>
  </Popover>

  <!-- ========== DESKTOP SIDEBAR ========== -->
  <aside class="hidden lg:flex flex-col fixed inset-y-0 left-0 w-60 z-[200] border-r border-surface-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">

    <!-- Logo area -->
    <div class="flex items-center gap-2.5 px-5 h-16 border-b border-surface-100 dark:border-zinc-800 shrink-0">
      <Logo class="h-9 w-auto text-primary shrink-0" />
      <span class="font-bold text-base tracking-tight">CarShare</span>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-3 py-4 space-y-5">
      <div v-for="(section, si) in navSections" :key="si" class="space-y-0.5">
        <p v-if="section.label"
          class="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-surface-400 dark:text-surface-500">
          {{ section.label }}
        </p>
        <button
          v-for="item in section.items"
          :key="item.routeName"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group"
          :class="isActive(item.routeName)
            ? 'bg-primary/10 text-primary dark:bg-primary/20'
            : 'text-slate-600 dark:text-slate-400 hover:bg-surface-100 dark:hover:bg-zinc-800 hover:text-slate-900 dark:hover:text-slate-100'"
          @click="navigate(item.routeName)"
        >
          <i :class="[item.icon, 'text-[15px] shrink-0 transition-colors',
            isActive(item.routeName) ? 'text-primary' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300']" />
          <span class="flex-1 truncate text-left">{{ item.label }}</span>
          <span v-if="item.badge"
            class="flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-white text-[10px] font-bold">
            {{ item.badge }}
          </span>
        </button>
      </div>
    </nav>

    <!-- Bottom: notifications, dark mode, user -->
    <div class="px-3 py-3 border-t border-surface-100 dark:border-zinc-800 space-y-0.5 shrink-0">
      <!-- Notifications -->
      <button
        class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all text-slate-600 dark:text-slate-400 hover:bg-surface-100 dark:hover:bg-zinc-800 hover:text-slate-900 dark:hover:text-slate-100 relative"
        @click="toggleNotifPopover($event)"
        aria-label="Notifications"
      >
        <i class="pi pi-bell text-[15px] text-slate-400 shrink-0" />
        <span class="flex-1 text-left">{{ $t('nav_notifications') }}</span>
        <span v-if="unreadCount > 0"
          class="flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold">
          {{ unreadCount }}
        </span>
      </button>

      <!-- Dark mode toggle -->
      <button
        class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all text-slate-600 dark:text-slate-400 hover:bg-surface-100 dark:hover:bg-zinc-800 hover:text-slate-900 dark:hover:text-slate-100"
        @click="toggleDarkMode"
      >
        <i :class="isDark ? 'pi pi-sun' : 'pi pi-moon'" class="text-[15px] text-slate-400 shrink-0" />
        <span>{{ isDark ? 'Light mode' : 'Dark mode' }}</span>
      </button>

      <!-- User info + logout -->
      <div class="flex items-center gap-3 px-3 py-2.5 rounded-xl mt-1">
        <div
          class="w-7 h-7 rounded-full bg-primary/15 text-primary flex items-center justify-center text-xs font-bold shrink-0 cursor-pointer hover:bg-primary/25 transition-colors"
          @click="navigate('profile')"
        >
          {{ userInitials }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate leading-tight">{{ auth.user?.full_name }}</p>
          <p class="text-[11px] text-surface-400 truncate">{{ auth.user?.email }}</p>
        </div>
        <button
          @click="logout"
          class="text-slate-400 hover:text-red-500 transition-colors p-1 rounded-lg"
          :title="$t('nav_logout')"
          aria-label="Logout"
        >
          <i class="pi pi-sign-out text-sm" />
        </button>
      </div>
    </div>
  </aside>

  <!-- ========== MOBILE TOP HEADER ========== -->
  <header
    class="lg:hidden fixed top-0 left-0 right-0 z-[200] flex flex-col border-b border-surface-200 dark:border-zinc-800 bg-white dark:bg-zinc-900"
  >
    <!-- Safe-area spacer: inherits the same background as the header -->
    <div style="height: env(safe-area-inset-top)" />

    <!-- Actual nav row: always exactly h-14 and vertically centered -->
    <div class="h-14 flex items-center justify-between px-3">
      <div class="flex items-center gap-2">
        <button
          class="w-9 h-9 flex items-center justify-center rounded-xl text-slate-500 hover:bg-surface-100 dark:hover:bg-zinc-800 transition-colors"
          @click="drawerVisible = true"
          aria-label="Open menu"
        >
          <i class="pi pi-bars text-base" />
        </button>
        <Logo class="h-8 w-auto text-primary" />
      </div>

      <div class="flex items-center gap-1">
        <button
          class="relative w-9 h-9 flex items-center justify-center rounded-xl text-slate-500 hover:bg-surface-100 dark:hover:bg-zinc-800 transition-colors"
          @click="toggleNotifPopover($event)"
          aria-label="Notifications"
        >
          <i class="pi pi-bell text-base" />
          <span v-if="unreadCount > 0"
            class="absolute top-1.5 right-1.5 flex items-center justify-center min-w-[14px] h-[14px] px-0.5 rounded-full bg-red-500 text-white text-[9px] font-bold leading-none">
            {{ unreadCount > 9 ? '9+' : unreadCount }}
          </span>
        </button>

        <button
          class="w-9 h-9 flex items-center justify-center rounded-xl text-slate-500 hover:bg-surface-100 dark:hover:bg-zinc-800 transition-colors"
          @click="toggleDarkMode"
          aria-label="Toggle dark mode"
        >
          <i :class="isDark ? 'pi pi-sun' : 'pi pi-moon'" class="text-base" />
        </button>

        <button
          class="w-8 h-8 rounded-full bg-primary/15 text-primary flex items-center justify-center text-xs font-bold hover:bg-primary/25 transition-colors"
          @click="navigate('profile')"
          aria-label="Profile"
        >
          {{ userInitials }}
        </button>
      </div>
    </div>
  </header>

  <!-- ========== MOBILE DRAWER ========== -->
  <Drawer v-model:visible="drawerVisible" class="!w-72">
    <template #container>
      <div class="flex flex-col h-full bg-white dark:bg-zinc-900">
        <!-- Drawer header -->
        <div class="flex items-center justify-between px-4 h-14 border-b border-surface-100 dark:border-zinc-800 shrink-0">
          <div class="flex items-center gap-2">
            <Logo class="h-8 w-auto text-primary" />
            <span class="font-bold">CarShare</span>
          </div>
          <button
            class="w-8 h-8 flex items-center justify-center rounded-xl text-slate-500 hover:bg-surface-100 dark:hover:bg-zinc-800 transition-colors"
            @click="drawerVisible = false"
            aria-label="Close menu"
          >
            <i class="pi pi-times text-sm" />
          </button>
        </div>

        <!-- Nav items -->
        <nav class="flex-1 overflow-y-auto px-3 py-4 space-y-5">
          <div v-for="(section, si) in navSections" :key="si" class="space-y-0.5">
            <p v-if="section.label"
              class="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-surface-400 dark:text-surface-500">
              {{ section.label }}
            </p>
            <button
              v-for="item in section.items"
              :key="item.routeName"
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group"
              :class="isActive(item.routeName)
                ? 'bg-primary/10 text-primary dark:bg-primary/20'
                : 'text-slate-600 dark:text-slate-400 hover:bg-surface-100 dark:hover:bg-zinc-800'"
              @click="navigate(item.routeName)"
            >
              <i :class="[item.icon, 'text-[15px] shrink-0',
                isActive(item.routeName) ? 'text-primary' : 'text-slate-400']" />
              <span class="flex-1 truncate text-left">{{ item.label }}</span>
              <span v-if="item.badge"
                class="flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-white text-[10px] font-bold">
                {{ item.badge }}
              </span>
            </button>
          </div>
        </nav>

        <!-- Drawer user section -->
        <div class="px-3 py-3 border-t border-surface-100 dark:border-zinc-800 space-y-0.5 shrink-0">
          <div class="flex items-center gap-3 px-3 py-2.5">
            <div class="w-8 h-8 rounded-full bg-primary/15 text-primary flex items-center justify-center text-xs font-bold shrink-0">
              {{ userInitials }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium truncate">{{ auth.user?.full_name }}</p>
              <p class="text-xs text-surface-400 truncate">{{ auth.user?.email }}</p>
            </div>
          </div>
          <button
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            @click="logout"
          >
            <i class="pi pi-sign-out text-[15px]" />
            <span>{{ $t('nav_logout') }}</span>
          </button>
        </div>
      </div>
    </template>
  </Drawer>

  <!-- ========== MOBILE BOTTOM NAV ========== -->
  <nav
    class="lg:hidden fixed bottom-0 left-0 right-0 z-[200] border-t border-surface-200 dark:border-zinc-800 bg-white dark:bg-zinc-900"
  >
    <div class="flex items-stretch">
      <button
        class="flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors min-h-[56px]"
        :class="isActive('home') ? 'text-primary' : 'text-slate-400'"
        @click="navigate('home')"
      >
        <i class="pi pi-home text-lg" />
        <span>{{ $t('nav_dashboard') }}</span>
      </button>

      <button v-if="isCarBorrower"
        class="flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors min-h-[56px]"
        :class="isActive('reserve car') ? 'text-primary' : 'text-slate-400'"
        @click="navigate('reserve car')"
      >
        <i class="pi pi-calendar-plus text-lg" />
        <span>{{ $t('nav_reserve') }}</span>
      </button>

      <button v-if="isCarBorrower"
        class="flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors min-h-[56px]"
        :class="isActive('borrowerappointments') ? 'text-primary' : 'text-slate-400'"
        @click="navigate('borrowerappointments')"
      >
        <i class="pi pi-list text-lg" />
        <span>{{ $t('nav_my_appointments') }}</span>
      </button>

      <button v-if="isCarOwner"
        class="flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors min-h-[56px] relative"
        :class="isActive('ownerappointments') ? 'text-primary' : 'text-slate-400'"
        @click="navigate('ownerappointments')"
      >
        <span class="relative inline-block">
          <i class="pi pi-inbox text-lg" />
          <span v-if="pendingBookingsCount > 0"
            class="absolute -top-1 -right-2 flex items-center justify-center min-w-[14px] h-[14px] px-0.5 rounded-full bg-primary text-white text-[9px] font-bold leading-none">
            {{ pendingBookingsCount }}
          </span>
        </span>
        <span>{{ $t('nav_appointments') }}</span>
      </button>

      <button
        class="flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors min-h-[56px]"
        :class="isActive('profile') ? 'text-primary' : 'text-slate-400'"
        @click="navigate('profile')"
      >
        <i class="pi pi-user text-lg" />
        <span>{{ $t('nav_my_profile') }}</span>
      </button>
    </div>
  </nav>
</template>
