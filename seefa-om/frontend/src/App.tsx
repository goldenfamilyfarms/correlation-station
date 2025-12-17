import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DocsLayout from './components/DocsLayout'
import HomePage from './pages/HomePage'
import DocumentationPage from './pages/DocumentationPage'
import ArchitecturePage from './pages/ArchitecturePage'
import SecaReviewsPage from './pages/SecaReviewsPage'
import NetDev101Page from './pages/NetDev101Page'
import SecaUploadPage from './pages/SecaUploadPage'
import CorrelationEnginePage from './pages/CorrelationEnginePage'
import CompliancePage from './pages/CompliancePage'
import LoginPage from './pages/LoginPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'

function App() {
  return (
    <BrowserRouter basename="/correlation-station">
      <Routes>
        {/* Auth routes - no layout */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Main app routes with global sidebar */}
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="architecture" element={<ArchitecturePage />} />
          <Route path="seca-review" element={<SecaReviewsPage />} />
          <Route path="seca-upload" element={<SecaUploadPage />} />
          <Route path="netdev101" element={<NetDev101Page />} />
          <Route path="correlation-engine" element={<CorrelationEnginePage />} />
          <Route path="compliance" element={<CompliancePage />} />
        </Route>

        {/* Documentation routes with docs-specific layout */}
        <Route path="/docs" element={<DocsLayout />}>
          <Route index element={<DocumentationPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App