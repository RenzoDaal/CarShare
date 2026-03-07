import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";
import LoginPage from "@/pages/LoginPage.vue";
import HomePage from "@/pages/HomePage.vue";
import CarManagerPage from "@/pages/CarManagerPage.vue";
import ReserveCarPage from "@/pages/ReserveCarPage.vue";
import OwnerAppointmentsPage from "@/pages/OwnerAppointmentsPage.vue";
import BorrowersAppointmentsPage from "@/pages/BorrowerAppointmentsPage.vue";
import CarAvailabilityPage from "@/pages/CarAvailabilityPage.vue";
import RegisterPage from "@/pages/RegisterPage.vue";
import AdminPage from "@/pages/AdminPage.vue";
import ProfilePage from "@/pages/ProfilePage.vue";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage.vue";
import ResetPasswordPage from "@/pages/ResetPasswordPage.vue";
import BookingDetailPage from "@/pages/BookingDetailPage.vue";
import { useAuthStore } from "@/stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: LoginPage,
    meta: { hideLayout: true, title: "Login" },
  },
  {
    path: "/register",
    name: "register",
    component: RegisterPage,
    meta: { hideLayout: true, title: "Create account" },
  },
  {
    path: "/forgot-password",
    name: "forgot-password",
    component: ForgotPasswordPage,
    meta: { hideLayout: true, title: "Reset password" },
  },
  {
    path: "/reset-password",
    name: "reset-password",
    component: ResetPasswordPage,
    meta: { hideLayout: true, title: "Set new password" },
  },
  { path: "/", name: "home", component: HomePage, meta: { title: "Dashboard" } },
  {
    path: "/managecars",
    name: "manage cars",
    component: CarManagerPage,
    meta: { requiresOwner: true, title: "Manage Cars" },
  },
  {
    path: "/reservecar",
    name: "reserve car",
    component: ReserveCarPage,
    meta: { requiresBorrower: true, title: "Reserve a Car" },
  },
  {
    path: "/ownerappointments",
    name: "ownerappointments",
    component: OwnerAppointmentsPage,
    meta: { requiresOwner: true, title: "Appointments" },
  },
  {
    path: "/borrowerappointments",
    name: "borrowerappointments",
    component: BorrowersAppointmentsPage,
    meta: { requiresBorrower: true, title: "My Appointments" },
  },
  {
    path: "/availability",
    name: "availability",
    component: CarAvailabilityPage,
    meta: { requiresBorrower: true, title: "Car Availability" },
  },
  {
    path: "/admin",
    name: "admin",
    component: AdminPage,
    meta: { requiresAdmin: true, title: "Admin" },
  },
  {
    path: "/profile",
    name: "profile",
    component: ProfilePage,
    meta: { title: "My Profile" },
  },
  {
    path: "/bookings/:id",
    name: "booking-detail",
    component: BookingDetailPage,
    meta: { title: "Booking Summary" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { left: 0, top: 0 };
  },
});

router.beforeEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — CarShare` : "CarShare";

  const auth = useAuthStore();

  const publicRoutes = ["login", "register", "forgot-password", "reset-password"];

  if (!auth.isAuthenticated && !publicRoutes.includes(String(to.name))) {
    return { name: "login" };
  }

  if (auth.isAuthenticated && (to.name === "login" || to.name === "register")) {
    return { name: "home" };
  }

  if (to.meta.requiresOwner && !auth.user?.role_owner) {
    return { name: "home" };
  }

  if (to.meta.requiresBorrower && !auth.user?.role_borrower) {
    return { name: "home" };
  }

  if (to.meta.requiresAdmin && !auth.user?.is_admin) {
    return { name: "home" };
  }

  return true;
});

export default router;
