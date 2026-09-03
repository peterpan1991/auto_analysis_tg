import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Upload, Table, message, Alert, Space, Breadcrumb, Typography, Input, Radio } from 'antd'
import { InboxOutlined, ImportOutlined, FolderOutlined, FileOutlined } from '@ant-design/icons'
import type { Task, ChatMessage } from '../types'
import { taskApi, chatApi } from '../api'

const { Dragger } = Upload
const { TextArea } = Input

function ChatImport() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const [task, setTask] = useState<Task | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [importing, setImporting] = useState(false)
  const [fileContent, setFileContent] = useState<string>('')
  const [fileName, setFileName] = useState<string>('')
  const [folderPath, setFolderPath] = useState<string>('')
  const [importMode, setImportMode] = useState<'file' | 'folder'>('file')
  const [previewData, setPreviewData] = useState<ChatMessage[]>([])
  const [importLogs, setImportLogs] = useState<string[]>([])
  const pollTimerRef = useRef<number | null>(null)

  const pollImportStatus = async () => {
    if (!taskId) return
    
    try {
      const { data } = await chatApi.getImportStatus(Number(taskId))
      
      if (data.logs && data.logs.length > 0) {
        setImportLogs(data.logs)
      }
      
      if (data.status === 'completed') {
        message.success(`导入成功，共 ${data.message_count} 条消息`)
        fetchMessages()
        fetchTask()
        setImporting(false)
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
      } else if (data.status === 'failed') {
        message.error(data.error || '导入失败')
        await taskApi.updateTaskStatus(Number(taskId), 'failed')
        fetchTask()
        setImporting(false)
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
      }
    } catch (error) {
      console.error('轮询导入状态失败:', error)
    }
  }

  useEffect(() => {
    if (taskId) {
      fetchTask()
      fetchMessages()
    }
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [taskId])

  const fetchTask = async () => {
    try {
      const { data } = await taskApi.getTask(Number(taskId))
      setTask(data)
    } catch (error) {
      message.error('获取任务信息失败')
    }
  }

  const fetchMessages = async () => {
    try {
      const { data } = await chatApi.getMessages(Number(taskId))
      setMessages(data)
    } catch (error) {
      console.error('获取消息失败')
    }
  }

  const handleFileRead = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      setFileContent(content)
      setFileName(file.name)
      parsePreview(content)
    }
    reader.readAsText(file)
    return false
  }

  const parsePreview = (content: string) => {
    const parsed: ChatMessage[] = []
    
    const trimmedContent = content.trim()
    if (trimmedContent.startsWith('{') || trimmedContent.startsWith('[')) {
      try {
        const data = JSON.parse(trimmedContent)
        
        if (data.personal_information) {
          const messages = extractMessagesFromTelegramExport(data)
          messages.slice(0, 20).forEach((msg: any, index: number) => {
            parsed.push({
              id: index,
              task_id: Number(taskId),
              sender: msg.from || msg.from_id || 'Unknown',
              content: msg.content || '',
              timestamp: msg.date || msg.timestamp || new Date().toISOString(),
              message_type: 'text',
            })
          })
        } else if (data.messages) {
          const messages = Array.isArray(data.messages) ? data.messages : [data.messages]
          messages.slice(0, 20).forEach((msg: any, index: number) => {
            let text = msg.text || ''
            if (Array.isArray(text)) {
              text = text.map((t: any) => typeof t === 'string' ? t : t.text || '').join('')
            }
            parsed.push({
              id: index,
              task_id: Number(taskId),
              sender: msg.sender_name || msg.from || 'Unknown',
              content: text,
              timestamp: msg.date || new Date().toISOString(),
              message_type: 'text',
            })
          })
        }
      } catch (e) {
        console.error('JSON parse error:', e)
      }
    }
    
    if (parsed.length === 0) {
      const lines = content.split('\n').filter(line => line.trim())
      lines.slice(0, 20).forEach((line, index) => {
        const match = line.match(/^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*[-–]\s*(.+?)\s*[-–]\s*(.+)$/)
        if (match) {
          parsed.push({
            id: index,
            task_id: Number(taskId),
            sender: match[2].trim(),
            content: match[3].trim(),
            timestamp: match[1].trim(),
            message_type: 'text',
          })
        } else {
          const simpleMatch = line.match(/^(.+?):\s*(.+)$/)
          if (simpleMatch) {
            parsed.push({
              id: index,
              task_id: Number(taskId),
              sender: simpleMatch[1].trim(),
              content: simpleMatch[2].trim(),
              timestamp: new Date().toISOString(),
              message_type: 'text',
            })
          }
        }
      })
    }
    
    setPreviewData(parsed)
  }

  const extractMessagesFromTelegramExport = (data: any): any[] => {
    const messages: any[] = []
    
    if (data.chats && data.chats.list) {
      for (const chat of data.chats.list) {
        if (chat.messages) {
          for (const msg of chat.messages) {
            let text = msg.text || ''
            if (Array.isArray(text)) {
              text = text.map((t: any) => typeof t === 'string' ? t : t.text || '').join('')
            }
            messages.push({
              ...msg,
              content: text,
            })
          }
        }
      }
    }
    
    return messages
  }

  const handleImport = async () => {
    setImportLogs([])
    
    if (importMode === 'file') {
      if (!fileContent) {
        message.warning('请先选择文件')
        return
      }
      
      setImporting(true)
      try {
        await chatApi.importChat({
          task_id: Number(taskId),
          file_content: fileContent,
          file_name: fileName,
        })
        
        pollTimerRef.current = window.setInterval(pollImportStatus, 10000)
      } catch (error) {
        message.error('导入失败')
        setImporting(false)
      }
    } else {
      if (!folderPath) {
        message.warning('请输入文件夹路径')
        return
      }
      
      setImporting(true)
      try {
        await chatApi.importChat({
          task_id: Number(taskId),
          folder_path: folderPath,
        })
        
        pollTimerRef.current = window.setInterval(pollImportStatus, 10000)
      } catch (error: any) {
        message.error(error?.response?.data?.detail || '导入失败')
        setImporting(false)
      }
    }
  }

  const messageColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      width: 180,
    },
    {
      title: '发送者',
      dataIndex: 'sender',
      width: 150,
    },
    {
      title: '内容',
      dataIndex: 'content',
      ellipsis: true,
    },
  ]

  const disabled = importing || task?.status === 'imported'

  return (
    <div style={{ padding: 24 }}>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <a onClick={() => navigate('/tasks')}>任务列表</a> },
          { title: task?.name || '导入聊天记录' },
        ]}
      />

      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Card title="上传聊天记录">
          <Radio.Group 
            value={importMode} 
            onChange={(e) => setImportMode(e.target.value)}
            style={{ marginBottom: 16 }}
            disabled={disabled}
          >
            <Radio.Button value="file">
              <FileOutlined /> 单文件导入
            </Radio.Button>
            <Radio.Button value="folder">
              <FolderOutlined /> 文件夹导入
            </Radio.Button>
          </Radio.Group>

          {importMode === 'file' ? (
            <Dragger
              accept=".txt,.json,.csv"
              beforeUpload={handleFileRead}
              showUploadList={false}
              disabled={disabled}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持 .txt, .json, .csv 格式的 Telegram 聊天记录文件
              </p>
            </Dragger>
          ) : (
            <Card size="small" type="inner">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Typography.Text type="secondary">
                  输入 Telegram 导出的文件夹路径（包含 messages.json 文件的文件夹）
                </Typography.Text>
                <TextArea
                  placeholder="例如: e:\pl\project\python\tgData\account_3"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  rows={3}
                  disabled={disabled}
                />
                <Typography.Text type="warning">
                  注意：文件夹路径需要是服务器可访问的绝对路径
                </Typography.Text>
              </Space>
            </Card>
          )}

          {(fileName || folderPath) && (
            <Alert
              message={importMode === 'file' ? `已选择文件: ${fileName}` : `已选择文件夹: ${folderPath}`}
              type="success"
              style={{ marginTop: 16 }}
              action={
                <Button
                  type="primary"
                  icon={<ImportOutlined />}
                  loading={importing}
                  onClick={handleImport}
                  disabled={importMode === 'file' ? !fileContent : !folderPath}
                >
                  开始导入
                </Button>
              }
            />
          )}

          {importMode === 'file' && previewData.length > 0 && (
            <Card size="small" title="预览前20条" style={{ marginTop: 16 }}>
              <Table
                columns={messageColumns}
                dataSource={previewData}
                rowKey="id"
                pagination={false}
                size="small"
              />
            </Card>
          )}

          {importLogs.length > 0 && (
            <Card size="small" title="导入日志" style={{ marginTop: 16 }}>
              <div style={{ 
                maxHeight: 200, 
                overflowY: 'auto', 
                background: '#f5f5f5', 
                padding: 8, 
                borderRadius: 4,
                fontFamily: 'monospace',
                fontSize: 12
              }}>
                {importLogs.map((log, idx) => (
                  <div key={idx} style={{ marginBottom: 4 }}>{log}</div>
                ))}
              </div>
            </Card>
          )}
        </Card>

        {messages.length > 0 && (
          <Card title={`已导入的消息 (${messages.length} 条)`}>
            <Table
              columns={messageColumns}
              dataSource={messages}
              rowKey="id"
              pagination={{ pageSize: 20 }}
              size="small"
            />
          </Card>
        )}
      </Space>
    </div>
  )
}

export default ChatImport
