<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import { useConfirm } from 'primevue/useconfirm';
import http from '@/api/http';
import type { User } from '@/stores/auth';

const confirm = useConfirm();
const users = ref<User[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

async function fetchUsers() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await http.get<User[]>('/admin/users');
    users.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to load users';
  } finally {
    loading.value = false;
  }
}

async function approveUser(userId: number) {
  try {
    await http.post(`/admin/users/${userId}/approve`);
    await fetchUsers();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to approve user';
  }
}

function confirmDelete(userId: number, name: string) {
  confirm.require({
    message: `Are you sure you want to delete ${name}'s account? This cannot be undone.`,
    header: 'Delete user',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true },
    acceptProps: { label: 'Delete', severity: 'danger' },
    accept: async () => {
      try {
        await http.delete(`/admin/users/${userId}`);
        await fetchUsers();
      } catch (err: any) {
        error.value = err?.response?.data?.detail ?? 'Failed to delete user';
      }
    },
  });
}

onMounted(fetchUsers);
</script>

<template>
  <div class="p-4 flex flex-col gap-4 max-w-5xl mx-auto w-full">
    <h1 class="text-2xl font-semibold mb-2">Admin — User Management</h1>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div v-if="loading" class="flex justify-center items-center py-10">
      <ProgressSpinner />
    </div>

    <template v-else>
      <!-- Pending approval -->
      <Card class="mb-4">
        <template #title>Awaiting approval</template>
        <template #content>
          <div v-if="users.filter(u => !u.is_approved).length === 0" class="text-sm text-surface-500">
            No users awaiting approval.
          </div>
          <div class="flex flex-col gap-3">
            <div v-for="user in users.filter(u => !u.is_approved)" :key="user.id"
              class="border rounded-md p-3 flex flex-col gap-2 md:flex-row md:justify-between md:items-center">
              <div>
                <div class="font-semibold">{{ user.full_name }}</div>
                <div class="text-sm text-surface-500">{{ user.email }}</div>
                <div class="flex gap-1 mt-1">
                  <Tag v-if="user.role_owner" value="Owner" severity="info" />
                  <Tag v-if="user.role_borrower" value="Borrower" severity="secondary" />
                </div>
              </div>
              <div class="flex gap-2">
                <Button label="Approve" icon="pi pi-check" severity="success" @click="approveUser(user.id)" />
                <Button label="Delete" icon="pi pi-trash" severity="danger" outlined @click="confirmDelete(user.id, user.full_name)" />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- All approved users -->
      <Card>
        <template #title>All approved users</template>
        <template #content>
          <div v-if="users.filter(u => u.is_approved).length === 0" class="text-sm text-surface-500">
            No approved users yet.
          </div>
          <ul class="flex flex-col gap-2 text-sm">
            <li v-for="user in users.filter(u => u.is_approved)" :key="user.id"
              class="flex justify-between items-center border rounded-md p-2 gap-2">
              <div>
                <span class="font-medium">{{ user.full_name }}</span>
                <span class="ml-2 text-surface-500">{{ user.email }}</span>
              </div>
              <div class="flex items-center gap-2">
                <Tag v-if="user.is_admin" value="Admin" severity="warn" />
                <Tag v-if="user.role_owner" value="Owner" severity="info" />
                <Tag v-if="user.role_borrower" value="Borrower" severity="secondary" />
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
