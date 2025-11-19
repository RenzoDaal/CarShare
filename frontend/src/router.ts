import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";
import LoginPage from "./pages/LoginPage.vue";
import HomePage from "./pages/HomePage.vue";
import { useAuthStore } from "./stores/auth";

const routes: RouteRecordRaw[] = [
  { path: "/login", name: "login", component: LoginPage },
  { path: "/", name: "home", component: HomePage },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!auth.isAuthenticated && to.name !== "login") {
    return { name: "login" };
  }

  if (auth.isAuthenticated && to.name === "login") {
    return { name: "home" };
  }

  return true;
});

export default router;
