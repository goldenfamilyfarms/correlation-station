import { useState, useCallback } from 'react'
import { Upload, FileSpreadsheet, Download, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface UploadResult {
  status: 'success' | 'error'
  total_errors?: number
  scraped_errors?: number
  error_groups?: number
  download_urls?: {
    pdf: string
    xlsx: string
  }
  error?: string
}

export default function SecaUploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls')) {
        setFile(droppedFile)
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://austx-mdso-logs-02.chtrse.com/correlation-engine/seca/upload', {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (response.ok) {
        setResult(data)
        
        // Auto-download files
        if (data.download_urls) {
          setTimeout(() => {
            window.open(`http://austx-mdso-logs-02.chtrse.com/correlation-engine${data.download_urls.pdf}`, '_blank')
          }, 500)
          setTimeout(() => {
            window.open(`http://austx-mdso-logs-02.chtrse.com/correlation-engine${data.download_urls.xlsx}`, '_blank')
          }, 1000)
        }
      } else {
        setResult({ status: 'error', error: data.detail || 'Upload failed' })
      }
    } catch (error) {
      setResult({ status: 'error', error: 'Network error. Please try again.' })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">SECA Error Analysis</h1>
        <p className="text-[#6C757D]">
          Upload your SECA XLSX file for automated error analysis, traceback extraction, and report generation
        </p>
      </div>

      {/* Upload Area */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Upload XLSX File</CardTitle>
          <CardDescription>
            Drag and drop your SECA error spreadsheet or click to browse
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
              dragActive
                ? 'border-[#1B6AC7] bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            {file ? (
              <div className="space-y-4">
                <FileSpreadsheet className="h-16 w-16 mx-auto text-green-500" />
                <div>
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-[#6C757D]">{(file.size / 1024).toFixed(2)} KB</p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setFile(null)}
                  disabled={uploading}
                >
                  Remove
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <Upload className="h-16 w-16 mx-auto text-gray-400" />
                <div>
                  <p className="text-lg font-medium">
                    Drop your XLSX file here
                  </p>
                  <p className="text-sm text-[#6C757D] mt-1">or</p>
                </div>
                <label>
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileChange}
                    className="hidden"
                    disabled={uploading}
                  />
                  <Button variant="outline" className="cursor-pointer" disabled={uploading}>
                    Browse Files
                  </Button>
                </label>
              </div>
            )}
          </div>

          {file && !uploading && !result && (
            <div className="mt-6 flex justify-center">
              <Button
                onClick={handleUpload}
                size="lg"
              >
                <Upload className="h-5 w-5 mr-2" />
                Process XLSX
              </Button>
            </div>
          )}

          {uploading && (
            <div className="mt-6 text-center">
              <Loader2 className="h-8 w-8 mx-auto animate-spin text-[#1B6AC7] mb-2" />
              <p className="text-sm text-[#6C757D]">
                Processing XLSX, scraping reports, and generating analysis...
              </p>
              <p className="text-xs text-[#6C757D] mt-1">This may take a few minutes</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card className={result.status === 'success' ? 'border-green-500' : 'border-red-500'}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {result.status === 'success' ? (
                <>
                  <CheckCircle className="h-6 w-6 text-green-500" />
                  Processing Complete
                </>
              ) : (
                <>
                  <AlertCircle className="h-6 w-6 text-red-500" />
                  Processing Failed
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result.status === 'success' ? (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-[#1B6AC7]">
                      {result.total_errors}
                    </div>
                    <div className="text-sm text-[#6C757D]">Total Errors</div>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {result.scraped_errors}
                    </div>
                    <div className="text-sm text-[#6C757D]">Scraped Reports</div>
                  </div>
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-[#FF9800]">
                      {result.error_groups}
                    </div>
                    <div className="text-sm text-[#6C757D]">Error Groups</div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <h3 className="font-semibold mb-3">Download Reports</h3>
                  <div className="flex gap-3">
                    <Button
                      onClick={() => window.open(`http://austx-mdso-logs-02.chtrse.com/correlation-engine${result.download_urls?.pdf}`, '_blank')}
                      variant="outline"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      PDF Report
                    </Button>
                    <Button
                      onClick={() => window.open(`http://austx-mdso-logs-02.chtrse.com/correlation-engine${result.download_urls?.xlsx}`, '_blank')}
                      variant="outline"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Reformatted XLSX
                    </Button>
                  </div>
                  <p className="text-xs text-[#6C757D] mt-2">
                    Files should download automatically. Click above if they don't.
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-red-600">
                <p className="font-medium">Error: {result.error}</p>
                <p className="text-sm mt-2">Please check your file and try again.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Info */}
      <Card className="mt-6 bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="text-[#1B6AC7]">What happens during processing?</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-[#6C757D] space-y-2">
          <p>1. <strong>Parse XLSX:</strong> Extract circuit IDs, dates, and error messages</p>
          <p>2. <strong>Scrape Reports:</strong> Selenium automation fetches detailed logs from MDSO</p>
          <p>3. <strong>Extract Tracebacks:</strong> Python error traces are identified and categorized</p>
          <p>4. <strong>Generate PDF:</strong> Comprehensive report with Amazon Q debug prompts</p>
          <p>5. <strong>Reformat XLSX:</strong> Color-coded error groups, sorted and filtered</p>
        </CardContent>
      </Card>
    </div>
  )
}
