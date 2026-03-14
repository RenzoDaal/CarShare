<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import http from '@/api/http';
import type { User } from '@/stores/auth';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const confirm = useConfirm();
const toast = useToast();
const users = ref<User[]>([]);
const loading = ref(false);

const pendingUsers = computed(() => users.value.filter(u => !u.is_approved));
const approvedUsers = computed(() => users.value.filter(u => u.is_approved));

async function fetchUsers() {
  loading.value = true;
  try {
    const { data } = await http.get<User[]>('/admin/users');
    users.value = data;
  } catch (err: any) {
    toast.add({ severity: 'error', summary: err?.response?.data?.detail ?? t('admin_error_load'), life: 4000 });
  } finally {
    loading.value = false;
  }
}

async function approveUser(userId: number) {
  try {
    await http.post(`/admin/users/${userId}/approve`);
    await fetchUsers();
    toast.add({ severity: 'success', summary: t('admin_approve'), life: 2500 });
  } catch (err: any) {
    toast.add({ severity: 'error', summary: t('admin_error_approve'), detail: err?.response?.data?.detail, life: 4000 });
  }
}

function confirmDelete(userId: number, name: string) {
  confirm.require({
    message: `${t('admin_confirm_delete_header')} — ${name}`,
    header: t('admin_confirm_delete_header'),
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: t('admin_confirm_cancel'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('admin_confirm_delete_button'), severity: 'danger' },
    accept: async () => {
      try {
        await http.delete(`/admin/users/${userId}`);
        await fetchUsers();
        toast.add({ severity: 'info', summary: t('admin_confirm_delete_button'), life: 2500 });
      } catch (err: any) {
        toast.add({ severity: 'error', summary: t('admin_error_delete'), detail: err?.response?.data?.detail, life: 4000 });
      }
    },
  });
}

onMounted(fetchUsers);
</script>

<template>
  <div class="p-4 flex flex-col gap-4 max-w-5xl mx-auto w-full">
    <h1 class="text-2xl font-semibold mb-2">{{ $t('admin_title') }}</h1>

    <!-- Pending users summary strip -->
    <div v-if="pendingUsers.length > 0"
      class="flex items-center gap-3 p-3 rounded-xl bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
      <i class="pi pi-user-plus text-orange-500" />
      <span class="text-sm font-medium text-orange-700 dark:text-orange-300">
        {{ $t('admin_pending_count', { count: pendingUsers.length }) }}
      </span>
    </div>

    <!-- Skeleton screens matching the two-card layout -->
    <div v-if="loading" class="flex flex-col gap-4">
      <div class="rounded-xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5 animate-pulse space-y-4">
        <div class="h-4 bg-surface-200 dark:bg-zinc-700 rounded-full w-40" />
        <div class="flex flex-col gap-3">
          <div v-for="i in 2" :key="i" class="flex items-center justify-between p-3 rounded-lg border border-surface-100 dark:border-zinc-800">
            <div class="space-y-2">
              <div class="h-3.5 bg-surface-200 dark:bg-zinc-700 rounded-full w-32" />
              <div class="h-3 bg-surface-100 dark:bg-zinc-800 rounded-full w-48" />
              <div class="flex gap-1.5">
                <div class="h-5 w-14 bg-surface-200 dark:bg-zinc-700 rounded-full" />
              </div>
            </div>
            <div class="flex gap-2">
              <div class="h-8 w-20 bg-surface-200 dark:bg-zinc-700 rounded-lg" />
              <div class="h-8 w-16 bg-surface-200 dark:bg-zinc-700 rounded-lg" />
            </div>
          </div>
        </div>
      </div>
      <div class="rounded-xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5 animate-pulse space-y-3">
        <div class="h-4 bg-surface-200 dark:bg-zinc-700 rounded-full w-36" />
        <div v-for="i in 4" :key="i" class="flex items-center justify-between p-2 rounded border border-surface-100 dark:border-zinc-800">
          <div class="flex gap-2 items-center">
            <div class="h-3.5 bg-surface-200 dark:bg-zinc-700 rounded-full w-28" />
            <div class="h-3 bg-surface-100 dark:bg-zinc-800 rounded-full w-40" />
          </div>
          <div class="flex gap-1.5">
            <div class="h-5 w-12 bg-surface-200 dark:bg-zinc-700 rounded-full" />
            <div class="h-7 w-7 bg-surface-200 dark:bg-zinc-700 rounded-full" />
          </div>
        </div>
      </div>
    </div>

    <template v-else>
      <!-- Pending approval -->
      <Card class="mb-4">
        <template #title>{{ $t('admin_awaiting_approval_title') }}</template>
        <template #content>
          <div v-if="pendingUsers.length === 0" class="text-sm text-surface-500">
            {{ $t('admin_no_pending') }}
          </div>
          <div class="flex flex-col gap-3">
            <div v-for="user in pendingUsers" :key="user.id"
              class="border rounded-md p-3 flex flex-col gap-2 md:flex-row md:justify-between md:items-center">
              <div>
                <div class="font-semibold">{{ user.full_name }}</div>
                <div class="text-sm text-surface-500">{{ user.email }}</div>
                <div class="flex gap-1 mt-1">
                  <Tag v-if="user.role_owner" :value="$t('admin_role_owner')" severity="info" />
                  <Tag v-if="user.role_borrower" :value="$t('admin_role_borrower')" severity="secondary" />
                </div>
              </div>
              <div class="flex gap-2">
                <Button :label="$t('admin_approve')" icon="pi pi-check" severity="success" @click="approveUser(user.id)" />
                <Button :label="$t('admin_delete')" icon="pi pi-trash" severity="danger" outlined @click="confirmDelete(user.id, user.full_name)" />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- All approved users -->
      <Card>
        <template #title>{{ $t('admin_approved_users_title') }}</template>
        <template #content>
          <div v-if="approvedUsers.length === 0" class="text-sm text-surface-500">
            {{ $t('admin_no_approved') }}
          </div>
          <ul class="flex flex-col gap-2 text-sm">
            <li v-for="user in approvedUsers" :key="user.id"
              class="flex flex-col gap-2 sm:flex-row sm:justify-between sm:items-center border rounded-md p-2">
              <div>
                <span class="font-medium">{{ user.full_name }}</span>
                <span class="ml-2 text-surface-500">{{ user.email }}</span>
              </div>
              <div class="flex items-center gap-2 flex-wrap">
                <Tag v-if="user.is_admin" :value="$t('admin_role_admin')" severity="warn" />
                <Tag v-if="user.role_owner" :value="$t('admin_role_owner')" severity="info" />
                <Tag v-if="user.role_borrower" :value="$t('admin_role_borrower')" severity="secondary" />
                <Button icon="pi pi-trash" severity="danger" outlined rounded size="small"
                  @click="confirmDelete(user.id, user.full_name)" />
              </div>
            </li>
          </ul>
        </template>
      </Card>
    </template>
  </div>
</template>
