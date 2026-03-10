import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "@/App.vue";
import router from "./router";
import { i18n } from './i18n';
import "@/assets/main.css";
import "@/assets/tailwind.css";
import "leaflet/dist/leaflet.css";
import ConfirmationService from "primevue/confirmationservice";
import ToastService from 'primevue/toastservice';

import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";
import { definePreset } from "@primeuix/themes";
import "primeicons/primeicons.css";
import { useAuthStore } from "@/stores/auth";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
useAuthStore().loadFromStorage();
app.use(ConfirmationService);
app.use(ToastService);

const MyTheme = definePreset(Aura, {
  semantic: {
    primary: {
      //500: "#ff7f00", // Only override “primary-500”
    },
  },
});

app.use(PrimeVue, {
  theme: {
    preset: MyTheme,
    options: {
      darkModeSelector: '.dark',
    },
  },
});

// Apply saved dark mode preference before first render
if (localStorage.getItem('darkMode') === 'true') {
  document.documentElement.classList.add('dark');
}

app.use(router);
app.use(i18n);
app.mount("#app");
