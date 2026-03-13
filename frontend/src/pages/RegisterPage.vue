<script setup lang="ts">
import { reactive, ref } from 'vue';
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
import Logo from '@/assets/logo.svg';
import http from '@/api/http';

const { t } = useI18n();

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
          z.string().min(1, { message: t('register_error_email_required') })
            .email({ message: t('register_error_email_invalid') }),
        ),
        password: stringFromNullish(
          z.string().min(6, { message: t('register_error_password_min') }),
        ),
        confirmPassword: stringFromNullish(
          z.string().min(1, { message: t('register_error_confirm_password_required') }),
        ),
        role_owner: z.preprocess((val) => (val == null ? false : val), z.boolean()),
        role_borrower: z.preprocess((val) => (val == null ? true : val), z.boolean()),
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
    error.value = e?.response?.data?.detail ?? t('register_error_fallback');
  } finally {
    submitting.value = false;
  }
};
</script>

<template>
  <div class="min-h-screen flex">
    <!-- Left brand panel (desktop only) -->
    <div class="hidden lg:flex lg:w-[45%] xl:w-1/2 bg-gradient-to-br from-primary via-primary/90 to-primary/70 flex-col items-center justify-center p-12 text-white relative overflow-hidden">
      <div class="absolute inset-0 overflow-hidden pointer-events-none">
        <div class="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-white/5" />
        <div class="absolute -bottom-12 -left-12 w-64 h-64 rounded-full bg-white/5" />
        <div class="absolute top-1/2 left-1/4 w-48 h-48 rounded-full bg-white/5" />
      </div>

      <div class="relative z-10 max-w-sm w-full">
        <div class="flex items-center gap-3 mb-10">
          <Logo class="h-12 w-auto text-white" />
          <span class="font-bold text-2xl tracking-tight">CarShare</span>
        </div>

        <h1 class="text-4xl font-bold mb-4 leading-tight">
          Meld je aan.<br>Begin vandaag.
        </h1>
        <p class="text-white/75 text-lg mb-12 leading-relaxed">
          Maak een account aan als eigenaar, lener of allebei.
        </p>

        <div class="space-y-4">
          <div class="flex items-start gap-4 bg-white/10 backdrop-blur-sm rounded-2xl p-4">
            <div class="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center shrink-0 mt-0.5">
              <i class="pi pi-shield text-lg" />
            </div>
            <div>
              <p class="font-semibold mb-0.5">Veilig & privé</p>
              <p class="text-sm text-white/65">Jouw gegevens zijn altijd beschermd</p>
            </div>
          </div>
          <div class="flex items-start gap-4 bg-white/10 backdrop-blur-sm rounded-2xl p-4">
            <div class="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center shrink-0 mt-0.5">
              <i class="pi pi-users text-lg" />
            </div>
            <div>
              <p class="font-semibold mb-0.5">Eigenaar én lener</p>
              <p class="text-sm text-white/65">Kies één of beide rollen — aanpasbaar in je profiel</p>
            </div>
          </div>
          <div class="flex items-start gap-4 bg-white/10 backdrop-blur-sm rounded-2xl p-4">
            <div class="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center shrink-0 mt-0.5">
              <i class="pi pi-bell text-lg" />
            </div>
            <div>
              <p class="font-semibold mb-0.5">Realtime meldingen</p>
              <p class="text-sm text-white/65">Blijf op de hoogte van jouw boekingen</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right form panel -->
    <div class="flex-1 flex flex-col items-center justify-center px-6 py-10 bg-surface-50 dark:bg-zinc-950">
      <!-- Mobile logo -->
      <div class="lg:hidden flex items-center gap-2 mb-10">
        <Logo class="h-10 w-auto text-primary" />
        <span class="font-bold text-xl tracking-tight">CarShare</span>
      </div>

      <div class="w-full max-w-sm">
        <div class="mb-8">
          <h2 class="text-2xl font-bold tracking-tight mb-1">{{ $t('register_title') }}</h2>
          <p class="text-sm text-surface-500">
            {{ $t('login_no_account').replace('?', '') || 'Al een account?' }}
            <RouterLink :to="{ name: 'login' }" class="text-primary hover:underline font-medium">
              {{ $t('register_back_to_login') }}
            </RouterLink>
          </p>
        </div>

        <div class="bg-white dark:bg-zinc-900 rounded-2xl shadow-sm border border-surface-200 dark:border-zinc-700 p-6">
          <Form :resolver="resolver" @submit="onFormSubmit" v-slot="$form">
            <div class="flex flex-col gap-4">
              <!-- Full name -->
              <div class="flex flex-col gap-1.5">
                <label class="text-sm font-medium">{{ $t('register_full_name_placeholder') }}</label>
                <InputText name="full_name" v-model="form.full_name"
                  :placeholder="$t('register_full_name_placeholder')"
                  :invalid="$form.full_name?.invalid" />
                <Message v-if="$form.full_name?.invalid" severity="error" size="small" variant="simple">
                  {{ $form.full_name.error?.message }}
                </Message>
              </div>

              <!-- Email -->
              <div class="flex flex-col gap-1.5">
                <label class="text-sm font-medium">{{ $t('register_email_placeholder') }}</label>
                <InputText name="email" v-model="form.email"
                  :placeholder="$t('register_email_placeholder')"
                  :invalid="$form.email?.invalid" />
                <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
                  {{ $form.email.error?.message }}
                </Message>
              </div>

              <!-- Password -->
              <div class="flex flex-col gap-1.5">
                <label class="text-sm font-medium">{{ $t('register_password_placeholder') }}</label>
                <Password name="password" v-model="form.password" :feedback="false" toggleMask class="w-full"
                  inputClass="w-full" :inputProps="{ placeholder: $t('register_password_placeholder') }"
                  :invalid="$form.password?.invalid" />
                <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
                  {{ $form.password.error?.message }}
                </Message>
              </div>

              <!-- Confirm password -->
              <div class="flex flex-col gap-1.5">
                <label class="text-sm font-medium">{{ $t('register_confirm_password_placeholder') }}</label>
                <Password name="confirmPassword" v-model="form.confirmPassword" :feedback="false" toggleMask
                  class="w-full" inputClass="w-full"
                  :inputProps="{ placeholder: $t('register_confirm_password_placeholder') }"
                  :invalid="$form.confirmPassword?.invalid" />
                <Message v-if="$form.confirmPassword?.invalid" severity="error" size="small" variant="simple">
                  {{ $form.confirmPassword.error?.message }}
                </Message>
              </div>

              <!-- Roles -->
              <div class="flex flex-col gap-2">
                <label class="text-sm font-medium">{{ $t('profile_roles_label') }}</label>
                <div class="flex gap-3">
                  <label
                    class="flex-1 flex items-center gap-2.5 p-3 rounded-xl border-2 cursor-pointer transition-all"
                    :class="form.role_owner
                      ? 'border-primary bg-primary/5 dark:bg-primary/10'
                      : 'border-surface-200 dark:border-zinc-700 hover:border-surface-300'"
                  >
                    <Checkbox name="role_owner" v-model="form.role_owner" :binary="true" inputId="role_owner" />
                    <p class="text-sm font-medium">{{ $t('register_role_owner_label') }}</p>
                  </label>
                  <label
                    class="flex-1 flex items-center gap-2.5 p-3 rounded-xl border-2 cursor-pointer transition-all"
                    :class="form.role_borrower
                      ? 'border-primary bg-primary/5 dark:bg-primary/10'
                      : 'border-surface-200 dark:border-zinc-700 hover:border-surface-300'"
                  >
                    <Checkbox name="role_borrower" v-model="form.role_borrower" :binary="true" inputId="role_borrower" />
                    <p class="text-sm font-medium">{{ $t('register_role_borrower_label') }}</p>
                  </label>
                </div>
                <Message v-if="$form.role_borrower?.invalid" severity="error" size="small" variant="simple">
                  {{ $form.role_borrower.error?.message }}
                </Message>
              </div>

              <!-- Backend error -->
              <p v-if="error" class="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 rounded-xl px-3 py-2">
                {{ error }}
              </p>
              <p v-if="successMessage" class="text-green-600 dark:text-green-400 text-sm bg-green-50 dark:bg-green-900/20 rounded-xl px-3 py-2">
                {{ successMessage }}
              </p>

              <Button type="submit" :label="$t('register_button')" icon="pi pi-user-plus" iconPos="right"
                :loading="submitting" class="w-full" />
            </div>
          </Form>
        </div>
      </div>
    </div>
  </div>
</template>
