import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input, Button, Card, Spin, Typography, Avatar, Space, Progress, Alert, List, Select } from 'antd'
import { SendOutlined, ArrowLeftOutlined, RobotOutlined, UserOutlined, DatabaseOutlined } from '@ant-design/icons'
import { chatApi, vectorizeApi } from '../api'
import type { VectorizeStatus, VectorizeDetailStatus, ChatSource } from '../api'
import type { TaskContact } from '../types'

const { Text, Title } = Typography

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: ChatSource[]
}

function AIChat() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [contacts, setContacts] = useState<TaskContact[]>([])
  const [selectedContactId, setSelectedContactId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [vectorizeStatus, setVectorizeStatus] = useState<VectorizeStatus | null>(null)
  const [vectorizeDetail, setVectorizeDetail] = useState<VectorizeDetailStatus | null>(null)
  const [checkingStatus, setCheckingStatus] = useState(true)
  const [vectorizing, setVectorizing] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<any>(null)
  const pollTimerRef = useRef<number | null>(null)

  useEffect(() => {
    checkVectorizeStatus()
    fetchContacts()
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [taskId])

  const fetchContacts = async () => {
    if (!taskId) return

    try {
      const { data } = await chatApi.getContacts(Number(taskId))
      setContacts(data)
    } catch (error) {
      console.error('Failed to get contacts:', error)
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const checkVectorizeStatus = async () => {
    if (!taskId) return
    setCheckingStatus(true)
    try {
      const { data } = await vectorizeApi.getStatus(Number(taskId))
      setVectorizeStatus(data)

      if (data.is_vectorized) {
        setVectorizing(false)
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
      }
    } catch (error) {
      console.error('Failed to check vectorize status:', error)
    } finally {
      setCheckingStatus(false)
    }
  }

  const startPollingDetailStatus = () => {
    if (pollTimerRef.current) return

    pollTimerRef.current = window.setInterval(async () => {
      if (!taskId) return
      try {
        const { data } = await vectorizeApi.getDetailStatus(Number(taskId))
        setVectorizeDetail(data)

        if (data.status === 'running') {
          setVectorizing(true)
          setVectorizeStatus(prev => prev ? { ...prev, progress: data.progress, embedding_count: data.embedding_count } : prev)
        } else if (data.status === 'completed') {
          setVectorizing(false)
          checkVectorizeStatus()
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
          }
        } else if (data.status === 'failed') {
          setVectorizing(false)
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
          }
        }
      } catch (error) {
        console.error('Failed to get detail status:', error)
      }
    }, 2000)
  }

  const handleStartVectorize = async () => {
    if (!taskId) return
    try {
      await vectorizeApi.startVectorize(Number(taskId))
      setVectorizing(true)
      startPollingDetailStatus()
    } catch (error) {
      console.error('Failed to start vectorize:', error)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = async () => {
    if (!inputValue.trim() || loading || !vectorizeStatus?.is_vectorized) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setLoading(true)

    try {
      const { data } = await vectorizeApi.chatAI({
        task_id: Number(taskId),
        prompt: userMessage.content,
        contact_id: selectedContactId,
      })

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        sources: data.sources,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: error.response?.data?.detail || '抱歉，AI服务暂时不可用，请稍后重试。',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  if (checkingStatus) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
        <Spin size="large" tip="检查向量化状态..." />
      </div>
    )
  }

  if (!vectorizeStatus?.is_vectorized) {
    return (
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f5f5' }}>
        <Card
          style={{ borderRadius: 0, flexShrink: 0 }}
          bodyStyle={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 16 }}
        >
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
            返回
          </Button>
          <Text strong style={{ fontSize: 16 }}>
            AI 对话 - 任务 #{taskId}
          </Text>
        </Card>

        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
          <Card style={{ maxWidth: 500, width: '100%' }}>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <DatabaseOutlined style={{ fontSize: 64, color: '#faad14', marginBottom: 16 }} />
              <Title level={4}>需要先向量化聊天记录</Title>
              <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                AI 对话功能需要先将聊天记录向量化，以便进行语义检索
              </Text>
            </div>

            {vectorizeStatus && (
              <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>消息数量: {vectorizeStatus.message_count}</Text>
                  <Text>已向量化: {vectorizeStatus.messages_processed}</Text>
                </div>
                <Progress percent={vectorizeStatus.progress} status="active" />
              </div>
            )}

            {vectorizeDetail?.error && (
              <Alert
                type="error"
                message="向量化失败"
                description={vectorizeDetail.error}
                style={{ marginBottom: 16 }}
              />
            )}

            {vectorizeDetail?.logs && vectorizeDetail.logs.length > 0 && (
              <List
                size="small"
                header="日志"
                dataSource={vectorizeDetail.logs}
                renderItem={(item) => <List.Item style={{ padding: '4px 0' }}>{item}</List.Item>}
                style={{ maxHeight: 150, overflow: 'auto', marginBottom: 16, textAlign: 'left' }}
              />
            )}

            <Button
              type="primary"
              size="large"
              icon={<DatabaseOutlined />}
              onClick={handleStartVectorize}
              loading={vectorizing}
              block
            >
              {vectorizeDetail?.status === 'running' ? '向量化中...' : '开始向量化'}
            </Button>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f5f5' }}>
      <Card
        style={{ borderRadius: 0, flexShrink: 0 }}
        bodyStyle={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 16 }}
      >
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
          返回
        </Button>
        <Text strong style={{ fontSize: 16 }}>
          AI 对话 - 任务 #{taskId}
        </Text>
      </Card>

      <div style={{ flex: 1, overflow: 'auto', padding: '24px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          {messages.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
              <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <Text style={{ display: 'block', fontSize: 16 }}>
                欢迎使用 AI 对话功能
              </Text>
              <Text style={{ display: 'block', color: '#bbb', marginTop: 8 }}>
                您可以基于聊天记录与 AI 进行对话，获取分析 insights
              </Text>
              <Text style={{ display: 'block', color: '#bbb', marginTop: 16, fontSize: 12 }}>
                已向量化 {vectorizeStatus?.messages_processed || 0} 条消息
              </Text>
            </div>
          )}

          {messages.map(msg => (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: 16,
              }}
            >
              <div style={{
                display: 'flex',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                alignItems: 'flex-start',
                gap: 12,
                maxWidth: '80%',
              }}>
                <Avatar
                  icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                  style={{
                    background: msg.role === 'user' ? '#1890ff' : '#52c41a',
                    flexShrink: 0,
                  }}
                />
                <div style={{ minWidth: 0, width: msg.role === 'assistant' ? '100%' : 'auto' }}>
                  <div style={{
                    background: msg.role === 'user' ? '#1890ff' : '#fff',
                    color: msg.role === 'user' ? '#fff' : '#333',
                    padding: '12px 16px',
                    borderRadius: 12,
                    boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}>
                    {msg.content}
                  </div>
                  {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                    <details style={{ marginTop: 8 }}>
                      <summary style={{ cursor: 'pointer', color: '#1677ff', fontSize: 13 }}>
                        查看来源（{msg.sources.length}）
                      </summary>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                        {msg.sources.map(source => (
                          <div
                            key={`${msg.id}-${source.source_id}`}
                            style={{
                              padding: 12,
                              border: '1px solid #e8e8e8',
                              borderRadius: 8,
                              background: '#fafafa',
                            }}
                          >
                            <Text strong>来源{source.source_id}</Text>
                            <Text type="secondary" style={{ display: 'block', marginTop: 2, fontSize: 12 }}>
                              会话 #{source.contact_id} · 消息 {source.start_message_id}-{source.end_message_id} · 相似度 {source.similarity.toFixed(4)}
                            </Text>
                            <div
                              style={{
                                marginTop: 8,
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                maxHeight: 240,
                                overflow: 'auto',
                                fontSize: 13,
                                lineHeight: 1.6,
                              }}
                            >
                              {source.content}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                  <Text style={{
                    display: 'block',
                    marginTop: 4,
                    fontSize: 12,
                    color: '#999',
                    textAlign: msg.role === 'user' ? 'right' : 'left',
                  }}>
                    {formatTime(msg.timestamp)}
                  </Text>
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, maxWidth: '80%' }}>
                <Avatar icon={<RobotOutlined />} style={{ background: '#52c41a', flexShrink: 0 }} />
                <div style={{ background: '#fff', padding: '12px 16px', borderRadius: 12, boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}>
                  <Space>
                    <Spin size="small" />
                    <Text style={{ color: '#999' }}>AI 正在思考...</Text>
                  </Space>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <Card style={{ borderRadius: 0, flexShrink: 0 }} bodyStyle={{ padding: '16px 24px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <Select
            allowClear
            value={selectedContactId}
            placeholder="全部会话"
            options={contacts.map(contact => ({
              value: contact.id,
              label: `${contact.name}${contact.is_group ? '（群聊）' : ''}`,
            }))}
            onChange={value => {
              setSelectedContactId(value)
              setMessages([])
            }}
            disabled={loading}
            style={{ width: '100%', marginBottom: 12 }}
          />
          <Input.TextArea
            ref={inputRef}
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="输入您的问题，按 Enter 发送..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ borderRadius: 8 }}
          />
          <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              disabled={!inputValue.trim()}
            >
              发送
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default AIChat
