import axios from 'axios'
import type { AxiosInstance } from 'axios'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})
