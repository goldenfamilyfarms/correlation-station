import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import DocumentationPage from './pages/DocumentationPage'
import ArchitecturePage from './pages/ArchitecturePage'
import SecaReviewsPage from './pages/SecaReviewsPage'
import NetDev101Page from './pages/NetDev101Page'
import SecaUploadPage from './pages/SecaUploadPage'
import CorrelationEnginePage from './pages/CorrelationEnginePage'

function App() {
  return (
    <BrowserRouter basename="/correlation-station">
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="docs" element={<DocumentationPage />} />
          <Route path="architecture" element={<ArchitecturePage />} />
          <Route path="seca-review" element={<SecaReviewsPage />} />
          <Route path="seca-upload" element={<SecaUploadPage />} />
          <Route path="netdev101" element={<NetDev101Page />} />
          <Route path="correlation-engine" element={<CorrelationEnginePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App