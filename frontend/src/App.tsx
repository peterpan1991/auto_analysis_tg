import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import TaskList from './pages/TaskList'
import ChatImport from './pages/ChatImport'
import AnalysisResult from './pages/AnalysisResult'
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
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
