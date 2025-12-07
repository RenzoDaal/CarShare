import axios from "axios";
import { useAuthStore } from "../stores/auth";

const API_BASE =
  import.meta.env.VITE_API_BASE || `${window.location.origin}/api`;

const http = axios.create({
  baseURL: API_BASE,
});

http.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

export default http;
