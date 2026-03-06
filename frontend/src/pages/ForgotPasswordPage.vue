<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import http from '@/api/http';

const router = useRouter();
const email = ref('');
const submitting = ref(false);
const submitted = ref(false);
const error = ref<string | null>(null);

async function submit() {
  if (!email.value.trim()) return;
  submitting.value = true;
  error.value = null;
  try {
    await http.post('/auth/request-reset', { email: email.value });
    submitted.value = true;
  } catch {
    error.value = 'Something went wrong. Please try again.';
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="flex-1 flex justify-center items-center h-screen">
    <Card>
      <template #title>Reset password</template>
      <template #content>
        <div class="flex flex-col mt-4 w-96 gap-4">
          <template v-if="!submitted">
            <p class="text-sm text-surface-500">
              Enter your email address and we'll send you a link to reset your password.
            </p>
            <InputText v-model="email" placeholder="Email" @keyup.enter="submit" />
            <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
            <Button label="Send reset link" icon="pi pi-envelope" iconPos="right"
              :loading="submitting" :disabled="!email.trim()" @click="submit" />
          </template>

          <template v-else>
            <p class="text-sm text-green-600">
              If an account exists for that email, a reset link has been sent. Check your inbox.
            </p>
          </template>

          <p class="text-sm text-center">
            <RouterLink :to="{ name: 'login' }" class="text-blue-500 hover:underline">
              Back to login
            </RouterLink>
          </p>
        </div>
      </template>
    </Card>
  </div>
</template>
