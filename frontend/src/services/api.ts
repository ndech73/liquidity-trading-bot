import { apiClient } from '../shared/services/apiClient';

// Unified API Client: provides backward compatibility for legacy imports while using the shared client
export const api = apiClient;
export { apiClient };
export default apiClient;
