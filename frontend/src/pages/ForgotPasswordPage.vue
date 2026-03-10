<script setup lang="ts">
import { ref } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import http from '@/api/http';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

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
    error.value = t('forgot_password_error_fallback');
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="flex-1 flex justify-center items-center min-h-screen px-4 bg-gradient-to-br from-primary/5 via-transparent to-surface-100 dark:from-primary/10 dark:via-surface-950 dark:to-surface-900">
    <Card class="w-full max-w-sm">
      <template #title>{{ $t('forgot_password_title') }}</template>
      <template #content>
        <div class="flex flex-col mt-4 w-full gap-4">
          <template v-if="!submitted">
            <p class="text-sm text-surface-500">
              {{ $t('forgot_password_description') }}
            </p>
            <InputText v-model="email" :placeholder="$t('forgot_password_email_placeholder')" @keyup.enter="submit" />
            <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
            <Button :label="$t('forgot_password_send_button')" icon="pi pi-envelope" iconPos="right"
              :loading="submitting" :disabled="!email.trim()" @click="submit" />
          </template>

          <template v-else>
            <p class="text-sm text-green-600">
              {{ $t('forgot_password_success') }}
            </p>
          </template>

          <p class="text-sm text-center">
            <RouterLink :to="{ name: 'login' }" class="text-blue-500 hover:underline">
              {{ $t('forgot_password_back_to_login') }}
            </RouterLink>
          </p>
        </div>
      </template>
    </Card>
  </div>
</template>
