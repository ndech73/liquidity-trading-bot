import axios from 'axios';
import { ENV } from '../../config/env';

export const apiClient = axios.create({
  baseURL: ENV.API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Request Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);
