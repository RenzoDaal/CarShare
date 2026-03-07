import { defineStore } from "pinia";
import http from "../api/http";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role_owner: boolean;
  role_borrower: boolean;
  is_approved: boolean;
  is_admin: boolean;
  timezone: string;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

type LoginPayload = {
  email: string;
  password: string;
};

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as User | null,
    token: null as string | null,
    loading: false,
    error: null as string | null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
  },

  actions: {
    loadFromStorage() {
      // Check localStorage first (remember me), then sessionStorage (session only)
      const token =
        localStorage.getItem("auth_token") ??
        sessionStorage.getItem("auth_token");
      const userJson =
        localStorage.getItem("auth_user") ??
        sessionStorage.getItem("auth_user");
      if (token && userJson) {
        this.token = token;
        this.user = JSON.parse(userJson) as User;
      }
    },

    saveToStorage(remember: boolean) {
      // Always clear both storages first to avoid stale data in either
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      sessionStorage.removeItem("auth_token");
      sessionStorage.removeItem("auth_user");

      if (this.token && this.user) {
        const storage = remember ? localStorage : sessionStorage;
        storage.setItem("auth_token", this.token);
        storage.setItem("auth_user", JSON.stringify(this.user));
      }
    },

    async login(payload: LoginPayload, remember: boolean = true) {
      this.loading = true;
      this.error = null;
      try {
        const res = await http.post<TokenResponse>("/auth/login", payload);
        this.token = res.data.access_token;
        this.user = res.data.user;
        this.saveToStorage(remember);
      } catch (err: any) {
        this.error =
          err?.response?.data?.detail ??
          "Login failed. Please check your details.";
        throw err;
      } finally {
        this.loading = false;
      }
    },

    updateUser(user: User) {
      this.user = user;
      // Re-save with whichever storage currently holds the token
      const inLocal = !!localStorage.getItem("auth_token");
      this.saveToStorage(inLocal);
    },

    logout() {
      this.token = null;
      this.user = null;
      this.saveToStorage(false);
    },
  },
});
