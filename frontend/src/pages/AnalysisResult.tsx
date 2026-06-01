import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Table, Tag, Space, Breadcrumb, message, Tabs, Spin, Empty, Progress, Row, Col, Divider, Modal } from 'antd'
import ReactMarkdown from 'react-markdown'
import { ArrowLeftOutlined, PlayCircleOutlined, ReloadOutlined, SafetyOutlined, RobotOutlined, StopOutlined } from '@ant-design/icons'
import type { Task, ExtractedInfo, AnalysisResult } from '../types'
import { taskApi, extractApi, analysisApi } from '../api'

const infoTypeLabels: Record<ExtractedInfo['info_type'], string> = {
  phone: '手机号码',
  id_card: '身份证号',
  car_plate: '车牌号',
  bank_card: '银行卡号',
  email: '邮箱账号',
  virtual_account: '虚拟账号',
  password: '疑似密码',
  url: '链接',
  domain: '域名',
  express: '快递单号',
  address: '地址',
}

const cleanMarkdown = (text: string): string => {
  return text
    .replace(/```[\w]*\n[\s\S]*?```/g, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/`[^`]+`/g, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/\|[^\n]+\|/g, '')
    .trim()
}

const infoTypeColors: Record<ExtractedInfo['info_type'], string> = {
  phone: 'blue',
  id_card: 'red',
  car_plate: 'green',
  bank_card: 'orange',
  email: 'purple',
  virtual_account: 'cyan',
  password: 'magenta',
  url: 'geekblue',
  domain: 'gold',
  express: 'lime',
  address: 'default',
}

const resultTypeLabels: Record<AnalysisResult['result_type'], string> = {
  person_info: '人员信息',
  org_structure: '组织架构',
  fund_flow: '资金流向',
  chat_topics: '聊天主题',
  location_info: '位置信息',
}

function AnalysisResult() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const [task, setTask] = useState<Task | null>(null)
  const [extractedInfo, setExtractedInfo] = useState<ExtractedInfo[]>([])
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([])
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [activeTab, setActiveTab] = useState('extracted')
  const [selectedInfoType, setSelectedInfoType] = useState<string | null>(null)
  const [extractedPage, setExtractedPage] = useState(1)
  const [modalVisible, setModalVisible] = useState(false)
  const [modalContent, setModalContent] = useState('')
  const [modalTitle, setModalTitle] = useState('')
  const [analysisLogs, setAnalysisLogs] = useState<string[]>([])
  const analyzePollTimerRef = useRef<number | null>(null)

  const pollAnalyzeStatus = async () => {
    if (!taskId) return
    
    try {
      const { data } = await analysisApi.getAnalyzeStatus(Number(taskId))
      
      if (data.logs && data.logs.length > 0) {
        setAnalysisLogs(data.logs)
      }
      
      if (data.status === 'completed') {
        message.success(`分析完成，共 ${data.result_count} 项结果`)
        setAnalyzing(false)
        fetchAnalysisResults()
        fetchTask()
        if (analyzePollTimerRef.current) {
          clearInterval(analyzePollTimerRef.current)
          analyzePollTimerRef.current = null
        }
      } else if (data.status === 'failed') {
        message.error(data.error || '分析失败')
        setAnalyzing(false)
        fetchTask()
        if (analyzePollTimerRef.current) {
          clearInterval(analyzePollTimerRef.current)
          analyzePollTimerRef.current = null
        }
      } else if (data.status === 'cancelled') {
        message.info('分析已取消')
        setAnalyzing(false)
        fetchTask()
        fetchAnalysisResults()
        if (analyzePollTimerRef.current) {
          clearInterval(analyzePollTimerRef.current)
          analyzePollTimerRef.current = null
        }
      }
    } catch (error) {
      console.error('轮询分析状态失败:', error)
    }
  }

  const filteredExtractedInfo = selectedInfoType 
    ? extractedInfo.filter(item => item.info_type === selectedInfoType)
    : extractedInfo

  const handleInfoTypeChange = (type: string | null) => {
    setSelectedInfoType(type)
    setExtractedPage(1)
  }

  useEffect(() => {
    if (taskId) {
      fetchTask()
      fetchExtractedInfo()
      fetchAnalysisResults()
    }
    return () => {
      if (analyzePollTimerRef.current) {
        clearInterval(analyzePollTimerRef.current)
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

  const fetchExtractedInfo = async () => {
    try {
      const { data } = await extractApi.getExtractedInfo(Number(taskId))
      setExtractedInfo(data)
    } catch (error) {
      console.error('获取提取信息失败')
    }
  }

  const fetchAnalysisResults = async () => {
    try {
      const { data } = await analysisApi.getResults(Number(taskId))
      setAnalysisResults(data)
    } catch (error) {
      console.error('获取分析结果失败')
    }
  }

  const handleExtract = async () => {
    setExtracting(true)
    try {
      await taskApi.updateTaskStatus(Number(taskId), 'analyzing')
      const { data } = await extractApi.extractInfo(Number(taskId))
      message.success(`提取完成，共提取 ${data.extracted_count} 条敏感信息`)
      fetchTask()
      fetchExtractedInfo()
    } catch (error) {
      message.error('提取失败')
      fetchTask()
    } finally {
      setExtracting(false)
    }
  }

  const handleAnalyze = async () => {
    setAnalysisLogs([])
    setAnalyzing(true)
    try {
      const { data } = await analysisApi.analyze(Number(taskId))
      if (data.result_count > 0) {
        message.success(`已有分析结果，共 ${data.result_count} 项`)
        setAnalyzing(false)
        fetchAnalysisResults()
        fetchTask()
      } else {
        analyzePollTimerRef.current = window.setInterval(pollAnalyzeStatus, 10000)
      }
    } catch (error) {
      message.error('分析失败')
      setAnalyzing(false)
    }
  }

  const extractedColumns = [
    {
      title: '联系人',
      dataIndex: 'contact_name',
      width: 120,
      render: (name: string | null) => name || '-',
    },
    {
      title: '发送者',
      dataIndex: 'sender',
      width: 120,
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'info_type',
      width: 100,
      render: (type: ExtractedInfo['info_type']) => (
        <Tag color={infoTypeColors[type]}>{infoTypeLabels[type]}</Tag>
      ),
    },
    {
      title: '内容',
      dataIndex: 'value',
      width: 180,
      ellipsis: true,
    },
    {
      title: '上下文',
      dataIndex: 'context',
      ellipsis: true,
    },
  ]

  const analysisColumns = [
    {
      title: '分析类型',
      dataIndex: 'result_type',
      width: 120,
      render: (type: AnalysisResult['result_type']) => (
        <Tag color="blue">{resultTypeLabels[type]}</Tag>
      ),
    },
    {
      title: '分析内容',
      dataIndex: 'content',
      render: (content: string) => {
        const cleanContent = cleanMarkdown(content)
        return (
          <a 
            onClick={() => {
              setModalContent(content)
              setModalTitle('分析详情')
              setModalVisible(true)
            }}
            style={{ color: '#595959' }}
          >
            {cleanContent.length > 200 ? cleanContent.substring(0, 200) + '...' : cleanContent}
          </a>
        )
      },
    },
    {
      title: '分析时间',
      dataIndex: 'created_at',
      width: 180,
    },
  ]

  const infoTypeCounts = extractedInfo.reduce((acc, item) => {
    acc[item.info_type] = (acc[item.info_type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div style={{ padding: 24 }}>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <a onClick={() => navigate('/tasks')}>任务列表</a> },
          { title: <a onClick={() => navigate(`/import/${taskId}`)}>{task?.name}</a> },
          { title: '分析结果' },
        ]}
      />

      <Card
        title={task?.name}
        extra={
          <Space>
            <Button
              type="primary"
              icon={<SafetyOutlined />}
              loading={extracting}
              onClick={handleExtract}
              disabled={task?.status === 'analyzing' || task?.status === 'completed' || task?.status === 'extracted'}
            >
              提取敏感信息
            </Button>
            <Button
              type="primary"
              icon={<RobotOutlined />}
              loading={analyzing}
              onClick={handleAnalyze}
              disabled={extracting || extractedInfo.length === 0}
            >
              AI智能分析
            </Button>
            {analyzing && (
              <Button
                danger
                icon={<StopOutlined />}
                onClick={async () => {
                  try {
                    await analysisApi.cancelAnalyze(Number(taskId))
                    message.info('已发送取消请求')
                  } catch (error) {
                    message.error('取消失败')
                  }
                }}
              >
                取消
              </Button>
            )}
          </Space>
        }
      >
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={4}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>{task?.message_count || 0}</div>
                <div>消息总数</div>
              </div>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>{extractedInfo.length}</div>
                <div>敏感信息</div>
              </div>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>{analysisResults.length}</div>
                <div>分析结果</div>
              </div>
            </Card>
          </Col>
        </Row>

        <Divider />

        {extractedInfo.length > 0 && (
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col span={4}>
              <Card 
                size="small" 
                hoverable
                onClick={() => handleInfoTypeChange(null)}
                style={{ 
                  textAlign: 'center',
                  borderColor: selectedInfoType === null ? '#1890ff' : undefined,
                  background: selectedInfoType === null ? '#e6f7ff' : undefined,
                }}
              >
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 'bold' }}>{extractedInfo.length}</div>
                  <div style={{ fontSize: 12 }}>全部</div>
                </div>
              </Card>
            </Col>
            {Object.entries(infoTypeLabels).map(([type, label]) => (
              <Col key={type} span={4}>
                <Card 
                  size="small" 
                  hoverable
                  onClick={() => handleInfoTypeChange(type)}
                  style={{ 
                    textAlign: 'center',
                    borderColor: selectedInfoType === type ? '#1890ff' : undefined,
                    background: selectedInfoType === type ? '#e6f7ff' : undefined,
                  }}
                >
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 18, fontWeight: 'bold' }}>{infoTypeCounts[type] || 0}</div>
                    <div style={{ fontSize: 12 }}>{label}</div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        )}

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'extracted',
              label: `敏感信息 (${extractedInfo.length})`,
              children: extractedInfo.length > 0 ? (
                <Table
                  columns={extractedColumns}
                  dataSource={filteredExtractedInfo}
                  rowKey="id"
                  pagination={{ pageSize: 20, current: extractedPage, onChange: setExtractedPage }}
                  size="small"
                />
              ) : (
                <Empty description="请点击「提取敏感信息」按钮开始提取" />
              ),
            },
            {
              key: 'analysis',
              label: `AI分析报告 (${analysisResults.length})`,
              children: (
                <>
                  {analyzing && analysisLogs.length > 0 && (
                    <Card size="small" title="分析日志" style={{ marginBottom: 16 }}>
                      <div style={{ 
                        maxHeight: 200, 
                        overflowY: 'auto', 
                        background: '#f5f5f5', 
                        padding: 8, 
                        borderRadius: 4,
                        fontFamily: 'monospace',
                        fontSize: 12
                      }}>
                        {analysisLogs.map((log, idx) => (
                          <div key={idx} style={{ marginBottom: 4 }}>{log}</div>
                        ))}
                      </div>
                    </Card>
                  )}
                  {analysisResults.length > 0 ? (
                    <Table
                      columns={analysisColumns}
                      dataSource={analysisResults}
                      rowKey="id"
                      pagination={false}
                      size="small"
                    />
                  ) : (
                    <Empty description="请点击「AI智能分析」按钮开始分析" />
                  )}
                </>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title={modalTitle}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={800}
      >
        <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          <ReactMarkdown>{modalContent}</ReactMarkdown>
        </div>
      </Modal>
    </div>
  )
}

export default AnalysisResult
