<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Checkbox from 'primevue/checkbox';
import Message from 'primevue/message';
import { Form } from '@primevue/forms';
import { z } from 'zod';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { stringFromNullish } from '@/utils/zod';
import { useI18n } from 'vue-i18n';

import http from '@/api/http';

const { t } = useI18n();
const router = useRouter();

const form = reactive({
  full_name: '',
  email: '',
  password: '',
  confirmPassword: '',
  role_owner: false,
  role_borrower: true,
});

const resolver = ref(
  zodResolver(
    z
      .object({
        full_name: stringFromNullish(
          z.string().min(1, { message: t('register_error_name_required') }),
        ),

        email: stringFromNullish(
          z
            .string()
            .min(1, { message: t('register_error_email_required') })
            .email({ message: t('register_error_email_invalid') }),
        ),

        password: stringFromNullish(
          z.string().min(6, {
            message: t('register_error_password_min'),
          }),
        ),

        confirmPassword: stringFromNullish(
          z.string().min(1, {
            message: t('register_error_confirm_password_required'),
          }),
        ),

        // Roles: make defaults match the UI
        role_owner: z.preprocess(
          (val) => (val == null ? false : val),
          z.boolean()
        ),
        role_borrower: z.preprocess(
          (val) => (val == null ? true : val),
          z.boolean()
        ),
      })
      .refine((data) => data.password === data.confirmPassword, {
        message: t('register_error_passwords_must_match'),
        path: ['confirmPassword'],
      })
      .refine((data) => data.role_owner || data.role_borrower, {
        message: t('register_error_select_role'),
        path: ['role_borrower'],
      }),
  ),
);

const submitting = ref(false);
const error = ref<string | null>(null);
const successMessage = ref<string | null>(null);

const onFormSubmit = async ({ valid }: { valid: boolean }) => {
  if (!valid) return;

  submitting.value = true;
  error.value = null;
  successMessage.value = null;

  try {
    await http.post('/auth/register', {
      email: form.email,
      password: form.password,
      full_name: form.full_name,
      role_owner: form.role_owner,
      role_borrower: form.role_borrower,
    });

    successMessage.value = t('register_success');
  } catch (e: any) {
    error.value =
      e?.response?.data?.detail ?? t('register_error_fallback');
  } finally {
    submitting.value = false;
  }
};

const goToLogin = () => {
  router.push({ name: 'login' });
};
</script>

<template>
  <div class="flex-1 flex justify-center items-center h-screen">
    <Card>
      <template #title>{{ $t('register_title') }}</template>
      <template #content>
        <Form :resolver="resolver" @submit="onFormSubmit" v-slot="$form">
          <div class="flex flex-col mt-4 w-96">
            <!-- Full name -->
            <div class="flex flex-col gap-1 mb-4">
              <InputText name="full_name" v-model="form.full_name" :placeholder="$t('register_full_name_placeholder')" />
              <Message v-if="$form.full_name?.invalid" severity="error" size="small" variant="simple">
                {{ $form.full_name.error?.message }}
              </Message>
            </div>

            <!-- Email -->
            <div class="flex flex-col gap-1 mb-4">
              <InputText name="email" v-model="form.email" :placeholder="$t('register_email_placeholder')" />
              <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
                {{ $form.email.error?.message }}
              </Message>
            </div>

            <!-- Password -->
            <div class="flex flex-col gap-1 mb-4">
              <Password name="password" v-model="form.password" :feedback="false" toggleMask class="w-full"
                inputClass="w-full" :inputProps="{ placeholder: $t('register_password_placeholder') }" />
              <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
                {{ $form.password.error?.message }}
              </Message>
            </div>

            <!-- Confirm password -->
            <div class="flex flex-col gap-1 mb-4">
              <Password name="confirmPassword" v-model="form.confirmPassword" :feedback="false" toggleMask
                class="w-full" inputClass="w-full" :inputProps="{ placeholder: $t('register_confirm_password_placeholder') }" />
              <Message v-if="$form.confirmPassword?.invalid" severity="error" size="small" variant="simple">
                {{ $form.confirmPassword.error?.message }}
              </Message>
            </div>

            <!-- Roles -->
            <div class="flex flex-col gap-1 mb-2 text-sm">
              <div class="flex items-center gap-2">
                <Checkbox name="role_owner" v-model="form.role_owner" :binary="true" inputId="role_owner" />
                <label for="role_owner">{{ $t('register_role_owner_label') }}</label>
              </div>
              <div class="flex items-center gap-2">
                <Checkbox name="role_borrower" v-model="form.role_borrower" :binary="true" inputId="role_borrower" />
                <label for="role_borrower">{{ $t('register_role_borrower_label') }}</label>
              </div>
              <Message v-if="$form.role_borrower?.invalid" severity="error" size="small" variant="simple">
                {{ $form.role_borrower.error?.message }}
              </Message>
            </div>

            <!-- Backend error -->
            <p v-if="error" class="text-red-500 text-sm mb-3">
              {{ error }}
            </p>

            <p v-if="successMessage" class="text-green-600 text-sm mb-3">
              {{ successMessage }}
            </p>

            <Button type="submit" :label="$t('register_button')" icon="pi pi-user-plus" iconPos="right" :loading="submitting" />

            <Button type="button" :label="$t('register_back_to_login')" class="mt-3" text @click="goToLogin" />
          </div>
        </Form>
      </template>
    </Card>
  </div>
</template>
