import axios from 'axios'
import type { Task, ChatMessage, ExtractedInfo, AnalysisResult, ImportRequest } from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 300000,
})

export const taskApi = {
  getTasks: () => api.get<Task[]>('/tasks'),
  getTask: (id: number) => api.get<Task>(`/tasks/${id}`),
  createTask: (name: string) => api.post<Task>('/tasks', { name }),
  deleteTask: (id: number) => api.delete(`/tasks/${id}`),
  updateTaskStatus: (id: number, status: Task['status']) => api.patch<Task>(`/tasks/${id}/status`, { status }),
}

export const chatApi = {
  getMessages: (taskId: number) => api.get<ChatMessage[]>(`/tasks/${taskId}/messages`),
  importChat: (data: ImportRequest) => api.post<{ message_count: number }>('/chat/import', data),
  getImportStatus: (taskId: number) => api.get<{ status: string; message_count: number; logs: string[]; error: string | null }>(`/tasks/${taskId}/import-status`),
  getImportLogs: (taskId: number) => api.get<{ logs: string[] }>(`/tasks/${taskId}/import-logs`),
}

export const extractApi = {
  extractInfo: (taskId: number) => api.post<{ extracted_count: number }>(`/tasks/${taskId}/extract`),
  getExtractedInfo: (taskId: number) => api.get<ExtractedInfo[]>(`/tasks/${taskId}/extracted`),
}

export const analysisApi = {
  analyze: (taskId: number) => api.post<{ result_count: number }>(`/tasks/${taskId}/analyze`),
  cancelAnalyze: (taskId: number) => api.post(`/tasks/${taskId}/analyze/cancel`),
  getResults: (taskId: number) => api.get<AnalysisResult[]>(`/tasks/${taskId}/analysis`),
  getAnalyzeStatus: (taskId: number) => api.get<{ status: string; result_count: number; logs: string[]; error: string | null }>(`/tasks/${taskId}/analyze-status`),
  getAnalyzeLogs: (taskId: number) => api.get<{ logs: string[] }>(`/tasks/${taskId}/analyze-logs`),
}

export interface VectorizeStatus {
  task_id: number
  message_count: number
  messages_processed: number
  is_vectorized: boolean
  progress: number
}

export interface VectorizeDetailStatus {
  status: string
  progress: number
  logs: string[]
  error: string | null
  embedding_count: number
}

export interface ChatAIRequest {
  task_id: number
  prompt: string
  top_k?: number
}

export interface ChatAIResponse {
  response: string
  context_messages: number
}

export const vectorizeApi = {
  getStatus: (taskId: number) => api.get<VectorizeStatus>(`/tasks/${taskId}/vectorize-status`),
  getDetailStatus: (taskId: number) => api.get<VectorizeDetailStatus>(`/tasks/${taskId}/vectorize-status-detail`),
  startVectorize: (taskId: number) => api.post(`/tasks/${taskId}/vectorize`),
  cancelVectorize: (taskId: number) => api.post(`/tasks/${taskId}/vectorize/cancel`),
  chatAI: (data: ChatAIRequest) => api.post<ChatAIResponse>('/chat/ai', data),
}

export default api
