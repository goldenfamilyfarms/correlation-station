import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import DocumentationPage from './pages/DocumentationPage'
import ArchitecturePage from './pages/ArchitecturePage'
import SecaReviewsPage from './pages/SecaReviewsPage'
import TutorialsPageNew from './pages/TutorialsPageNew'
import SecaUploadPage from './pages/SecaUploadPage'

function App() {
  return (
    <BrowserRouter basename="/correlation-station">
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="docs" element={<DocumentationPage />} />
          <Route path="architecture" element={<ArchitecturePage />} />
          <Route path="seca-reviews" element={<SecaReviewsPage />} />
          <Route path="tutorials" element={<TutorialsPageNew />} />
          <Route path="seca-upload" element={<SecaUploadPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App