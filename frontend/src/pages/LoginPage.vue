<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { z } from 'zod';
import { ref } from 'vue';
import { Form } from '@primevue/forms'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  email: '',
  password: '',
})

//const loading = computed(() => auth.loading)
//const error = computed(() => auth.error)

const resolver = ref(zodResolver(
  z.object({
    email: z.string().min(1, { message: 'Email is required' }),
    password: z.string().min(1, { message: 'Password is require' }),
  })
));

const onFormSubmit = async () => {
  console.log("TEST1");
  console.log(form.email);
  console.log(form.password);
  try {
    await auth.login({
      email: form.email,
      password: form.password,
    })
    console.log("TEST2");
    router.push({ name: 'home' })
  } catch (e) {
    console.log("TEST3", e);
    //auth.error already set in store
  }
};

</script>


<template>
  <div class="flex-1 flex justify-center items-center h-screen">
    <Card>
      <template #title>Login Page</template>
      <template #content>
        <Form 
          :resolver
          @submit="onFormSubmit"
        >
          <div class="flex flex-col mt-4 w-96">
            <InputText 
              class="mb-4"
              name="email" 
              v-model="form.email" 
              placeholder="Username" 
            /> 
            <InputText
              class="mb-4"
              name="password" 
              v-model="form.password"
              placeholder="Password" 
            />

            <Button
              type="submit"
              label="Login"
              icon="pi pi-sign-in"
              iconPos="right"
            />
          </div>
        </Form>
      </template>
    </Card>
  </div>
</template>
