import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import TaskList from './pages/TaskList'
import ChatImport from './pages/ChatImport'
import AnalysisResult from './pages/AnalysisResult'
import AIChat from './pages/AIChat'
import './App.css'

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/tasks" replace />} />
          <Route path="/tasks" element={<TaskList />} />
          <Route path="/import/:taskId" element={<ChatImport />} />
          <Route path="/analysis/:taskId" element={<AnalysisResult />} />
          <Route path="/ai-chat/:taskId" element={<AIChat />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
