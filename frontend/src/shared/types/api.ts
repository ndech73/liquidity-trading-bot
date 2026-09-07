export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

export interface WebSocketMessage<T = unknown> {
  channel: string;
  type: string;
  data: T;
  timestamp: string;
}
