export interface Task {
  id: number
  name: string
  status: 'pending' | 'importing' | 'imported' | 'extracted' | 'analyzing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  message_count?: number
  error_message?: string
}

export interface ChatMessage {
  id: number
  task_id: number
  sender: string
  content: string
  timestamp: string
  message_type: 'text' | 'image' | 'file' | 'video' | 'audio' | 'other'
}

export interface ExtractedInfo {
  id: number
  task_id: number
  message_id: number | null
  contact_id: number | null
  info_type: 'phone' | 'id_card' | 'car_plate' | 'bank_card' | 'email' | 'virtual_account' | 'password' | 'url' | 'domain' | 'express' | 'address'
  value: string
  context: string
  confidence: number
  created_at: string
  sender: string | null
  contact_name: string | null
}

export interface AnalysisResult {
  id: number
  task_id: number
  result_type: 'person_info' | 'org_structure' | 'fund_flow' | 'chat_topics' | 'location_info'
  content: string
  created_at: string
}

export interface AnalysisRequest {
  task_id: number
}

export interface ImportRequest {
  task_id: number
  file_content?: string
  file_name?: string
  folder_path?: string
}
