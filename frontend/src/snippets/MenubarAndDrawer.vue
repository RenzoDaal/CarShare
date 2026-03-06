<script setup lang="ts">
  import Toolbar from 'primevue/toolbar';
  import Button from 'primevue/button';
  import Menu from 'primevue/menu';
  import Drawer from 'primevue/drawer';
  import Popover from 'primevue/popover';
  import Logo from '@/assets/logo.svg';

  import { ref, computed, onMounted, onUnmounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAuthStore } from '../stores/auth';
  import http from '@/api/http';

  type Notification = {
    id: number;
    message: string;
    is_read: boolean;
    created_at: string;
    booking_id?: number | null;
  };

  const auth = useAuthStore();
  const router = useRouter()

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
    } catch {
      // silently ignore
    }
  }

  async function toggleNotifPopover(event: Event) {
    notifPopover.value.toggle(event);
    if (unreadCount.value > 0) {
      await http.post('/notifications/read-all');
      notifications.value = notifications.value.map(n => ({ ...n, is_read: true }));
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
  const homeDrawerItems = ref([
    {
      label: 'Home',
      items: [
        {
          label: 'Dashboard',
          icon: 'pi pi-home',
          command: () => {
            router.push({ name: 'home' });
            drawerVisible.value = false;
          },
        },
        {
          label: 'My profile',
          icon: 'pi pi-user',
          command: () => {
            router.push({ name: 'profile' });
            drawerVisible.value = false;
          },
        }
      ]
    }
  ])

  const carOwnerDrawerItems = computed(() => [
    {
      label: 'Owner',
      items: [
        {
          label: 'Manage Cars',
          icon: 'pi pi-car',
          command: () => {
            router.push({ name: 'manage cars' });
            drawerVisible.value = false;
          }
        },
        {
          label: 'Appointments',
          icon: "pi pi-calendar",
          badge: pendingBookingsCount.value > 0 ? String(pendingBookingsCount.value) : undefined,
          badgeSeverity: 'warn',
          command: () => {
            router.push({ name: 'ownerappointments' });
            drawerVisible.value = false;
          }
        }
      ]
    }
  ]);

  const adminDrawerItems = ref([
    {
      label: 'Admin',
      items: [
        {
          label: 'User management',
          icon: 'pi pi-users',
          command: () => {
            router.push({ name: 'admin' });
            drawerVisible.value = false;
          }
        }
      ]
    }
  ]);

  const carBorrowerDrawerItems = ref([
    {
      label: 'Borrower',
      items: [
        {
          label: 'Reserve',
          icon: 'pi pi-calendar',
          command: () => {
            router.push({ name: 'reserve car' });
            drawerVisible.value = false;
          }
        },
        {
          label: 'My appointments',
          icon: 'pi pi-calendar',
          command:() => {
            router.push({ name: 'borrowerappointments' });
            drawerVisible.value = false;
          }
        },
        {
          label: 'Availability',
          icon: 'pi pi-calendar-clock',
          command: () => {
            router.push({ name: 'availability' });
            drawerVisible.value = false;
          }
        }
      ]
    }
  ]); 
</script>


<template>
  <Drawer v-model:visible="drawerVisible">
    <template #container>
      <Menu class="!border-none" :model=homeDrawerItems />
      <Menu class="!border-none" :model="carOwnerDrawerItems" v-if="isCarOwner"/>
      <Menu class="!border-none" :model="carBorrowerDrawerItems" v-if="isCarBorrower"/>
      <Menu class="!border-none" :model="adminDrawerItems" v-if="isAdmin"/>
      <div class="px-4 py-2">
        <Button label="Logout" icon="pi pi-sign-out" severity="secondary" variant="text" @click="logout" />
      </div>
    </template>
  </Drawer>
  <div>
    <Toolbar class="!border-none !rounded-none">
      <template #end>
        <Popover ref="notifPopover">
          <div class="w-80 flex flex-col">
            <div class="px-1 pb-2">
              <span class="font-semibold text-sm">Notifications</span>
            </div>
            <div v-if="notifications.length === 0" class="text-sm text-surface-500 py-4 text-center">
              No notifications yet
            </div>
            <ul v-else class="flex flex-col gap-1 max-h-80 overflow-y-auto">
              <li
                v-for="notif in notifications"
                :key="notif.id"
                class="text-sm px-2 py-2 rounded"
                :class="notif.is_read ? 'text-surface-500' : 'font-medium bg-surface-100 dark:bg-surface-800'"
              >
                {{ notif.message }}
              </li>
            </ul>
          </div>
        </Popover>
        <Button
          icon="pi pi-bell"
          variant="text"
          severity="secondary"
          rounded
          :badge="unreadCount > 0 ? String(unreadCount) : undefined"
          badgeSeverity="danger"
          @click="toggleNotifPopover"
        />
        <Button
          :icon="isDark ? 'pi pi-sun' : 'pi pi-moon'"
          variant="text"
          severity="secondary"
          rounded
          @click="toggleDarkMode"
        />
      </template>
      <template #start>
        <div class="flex items-center gap-4 ml-2">
          <Button 
            icon="pi pi-bars" 
            variant="text" 
            severity="secondary" 
            rounded
            @click="drawerVisible = true"
          />
          <div class="flex items-center gap-1">
            <Logo class="h-11 w-auto text-primary" />
          </div>
        </div>
      </template>
    </Toolbar>
  </div>
</template>
