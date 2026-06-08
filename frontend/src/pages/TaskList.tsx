import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Button, Modal, Form, Input, message, Popconfirm, Tag, Card } from 'antd'
import { PlusOutlined, DeleteOutlined, UploadOutlined, BarChartOutlined, RobotOutlined } from '@ant-design/icons'
import type { Task } from '../types'
import { taskApi } from '../api'

const statusColors: Record<Task['status'], string> = {
  pending: 'default',
  importing: 'processing',
  imported: 'blue',
  extracted: 'cyan',
  analyzing: 'orange',
  completed: 'green',
  failed: 'red',
}

const statusText: Record<Task['status'], string> = {
  pending: '待导入',
  importing: '导入中',
  imported: '已导入',
  extracted: '已提取',
  analyzing: '分析中',
  completed: '已完成',
  failed: '失败',
}

function TaskList() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const pollTimerRef = useRef<number | null>(null)

  const fetchTasks = async () => {
    setLoading(true)
    try {
      const { data } = await taskApi.getTasks()
      setTasks(data)
      
      const hasRunningTask = data.some((t: Task) => t.status === 'importing' || t.status === 'analyzing')
      if (hasRunningTask && !pollTimerRef.current) {
        pollTimerRef.current = window.setInterval(fetchTasks, 10000)
      } else if (!hasRunningTask && pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
    } catch (error) {
      message.error('获取任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [])

  const handleCreate = async (values: { name: string }) => {
    try {
      await taskApi.createTask(values.name)
      message.success('创建成功')
      setModalVisible(false)
      form.resetFields()
      fetchTasks()
    } catch (error) {
      message.error('创建失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await taskApi.deleteTask(id)
      message.success('删除成功')
      fetchTasks()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
    },
    {
      title: '任务名称',
      dataIndex: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: Task['status']) => (
        <Tag color={statusColors[status]}>{statusText[status]}</Tag>
      ),
    },
    {
      title: '消息数',
      dataIndex: 'message_count',
      width: 100,
      render: (count?: number) => count || 0,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
    },
    {
      title: '操作',
      width: 200,
      render: (_: unknown, record: Task) => (
        <>
          <Button
            type="link"
            icon={<UploadOutlined />}
            onClick={() => navigate(`/import/${record.id}`)}
            disabled={record.status === 'analyzing' || record.status === 'completed'}
          >
            导入
          </Button>
          <Button
            type="link"
            icon={<BarChartOutlined />}
            onClick={() => navigate(`/analysis/${record.id}`)}
            disabled={!['imported', 'extracted', 'completed'].includes(record.status)}
          >
            分析
          </Button>
          <Button
            type="link"
            icon={<RobotOutlined />}
            onClick={() => navigate(`/ai-chat/${record.id}`)}
            disabled={!['imported', 'extracted', 'completed'].includes(record.status)}
          >
            AI对话
          </Button>
          <Popconfirm
            title="确定删除此任务？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card title="任务管理" extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
          新建任务
        </Button>
      }>
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title="新建任务"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default TaskList
