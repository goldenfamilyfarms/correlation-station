import { useState, useRef } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Upload, FileText, CheckCircle2, XCircle, Download } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

interface SecaUploadModalProps {
  open: boolean
  onClose: () => void
  onSuccess?: (data: { pdfUrl?: string; xlsxUrl?: string; errorCount: number }) => void
}

type UploadStage = 'idle' | 'uploading' | 'parsing' | 'scraping' | 'generating' | 'complete' | 'error'

export function SecaUploadModal({ open, onClose, onSuccess }: SecaUploadModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [stage, setStage] = useState<UploadStage>('idle')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{
    pdfUrl?: string
    xlsxUrl?: string
    errorCount: number
    processedCount: number
  } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile && selectedFile.name.endsWith('.xlsx')) {
      setFile(selectedFile)
      setError(null)
    } else {
      setError('Please select a valid XLSX file')
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setStage('uploading')
    setProgress(10)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      // Stage 1: Upload
      setProgress(20)
      const uploadResponse = await fetch('/api/seca/upload', {
        method: 'POST',
        body: formData,
      })

      if (!uploadResponse.ok) {
        throw new Error('Upload failed')
      }

      // Stage 2: Parsing
      setStage('parsing')
      setProgress(40)

      // Stage 3: Scraping (simulated - backend handles this)
      setStage('scraping')
      setProgress(60)

      // Stage 4: Generating PDF/XLSX
      setStage('generating')
      setProgress(80)

      // Simulate processing time
      await new Promise((resolve) => setTimeout(resolve, 2000))

      const data = await uploadResponse.json()

      setProgress(100)
      setStage('complete')
      setResult({
        pdfUrl: data.download_urls?.pdf,
        xlsxUrl: data.download_urls?.xlsx,
        errorCount: data.total_errors || 0,
        processedCount: data.scraped_errors || 0,
      })

      if (onSuccess) {
        onSuccess({
          pdfUrl: data.download_urls?.pdf,
          xlsxUrl: data.download_urls?.xlsx,
          errorCount: data.total_errors || 0,
        })
      }
    } catch (err) {
      setStage('error')
      setError(err instanceof Error ? err.message : 'Processing failed')
    }
  }

  const handleReset = () => {
    setFile(null)
    setStage('idle')
    setProgress(0)
    setError(null)
    setResult(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleClose = () => {
    if (stage === 'complete' || stage === 'error') {
      handleReset()
    }
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Upload SECA Spreadsheet</DialogTitle>
          <DialogDescription>
            Upload your SECA Excel export for automated analysis and traceback extraction
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* File Upload */}
          {stage === 'idle' && (
            <div className="space-y-4">
              <div
                className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <p className="font-semibold mb-2">Click to upload or drag and drop</p>
                <p className="text-sm text-muted-foreground mb-4">XLSX files only</p>
                {file && (
                  <div className="mt-4 p-3 bg-muted rounded-lg">
                    <div className="flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      <span className="font-medium">{file.name}</span>
                    </div>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>
              {error && (
                <div className="p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
                  {error}
                </div>
              )}
              <Button
                onClick={handleUpload}
                disabled={!file}
                className="w-full"
              >
                Start Processing
              </Button>
            </div>
          )}

          {/* Processing Stages */}
          {(stage === 'uploading' || stage === 'parsing' || stage === 'scraping' || stage === 'generating') && (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">
                    {stage === 'uploading' && 'Uploading file...'}
                    {stage === 'parsing' && 'Parsing spreadsheet...'}
                    {stage === 'scraping' && 'Scraping Meta Web Tool...'}
                    {stage === 'generating' && 'Generating reports...'}
                  </span>
                  <span className="text-sm text-muted-foreground">{progress}%</span>
                </div>
                <Progress value={progress} />
              </div>

              <div className="space-y-2 text-sm">
                <div className={`flex items-center gap-2 ${progress >= 20 ? 'text-[#FF9800]' : 'text-muted-foreground'}`}>
                  {progress >= 20 ? <CheckCircle2 className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full border-2" />}
                  <span>File uploaded</span>
                </div>
                <div className={`flex items-center gap-2 ${progress >= 40 ? 'text-[#FF9800]' : 'text-muted-foreground'}`}>
                  {progress >= 40 ? <CheckCircle2 className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full border-2" />}
                  <span>XLSX parsed and filtered</span>
                </div>
                <div className={`flex items-center gap-2 ${progress >= 60 ? 'text-[#FF9800]' : 'text-muted-foreground'}`}>
                  {progress >= 60 ? <CheckCircle2 className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full border-2" />}
                  <span>Selenium scraping complete</span>
                </div>
                <div className={`flex items-center gap-2 ${progress >= 80 ? 'text-[#FF9800]' : 'text-muted-foreground'}`}>
                  {progress >= 80 ? <CheckCircle2 className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full border-2" />}
                  <span>PDF and XLSX generated</span>
                </div>
              </div>
            </div>
          )}

          {/* Success */}
          {stage === 'complete' && result && (
            <div className="space-y-4">
              <div className="p-4 bg-green-500/10 border border-green-500 rounded-lg">
                <div className="flex items-center gap-2 text-green-500 mb-2">
                  <CheckCircle2 className="h-5 w-5" />
                  <span className="font-semibold">Processing Complete!</span>
                </div>
                <div className="text-sm space-y-1">
                  <p>Total errors processed: {result.errorCount}</p>
                  <p>Errors with tracebacks: {result.processedCount}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {result.pdfUrl && (
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-5 w-5 text-[#FF9800]" />
                        <span className="font-semibold">Analysis PDF</span>
                      </div>
                      <p className="text-xs text-muted-foreground mb-3">
                        Contains tracebacks and Amazon Q Developer prompts
                      </p>
                      <Button size="sm" className="w-full" asChild>
                        <a href={result.pdfUrl} download>
                          <Download className="h-4 w-4 mr-2" />
                          Download PDF
                        </a>
                      </Button>
                    </CardContent>
                  </Card>
                )}

                {result.xlsxUrl && (
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-5 w-5 text-[#FF9800]" />
                        <span className="font-semibold">Reformatted XLSX</span>
                      </div>
                      <p className="text-xs text-muted-foreground mb-3">
                        Color-coded and sorted by error type
                      </p>
                      <Button size="sm" variant="outline" className="w-full" asChild>
                        <a href={result.xlsxUrl} download>
                          <Download className="h-4 w-4 mr-2" />
                          Download XLSX
                        </a>
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </div>

              <Button className="w-full" onClick={() => {
                handleClose()
                // Navigate to SECA Review page
                window.location.href = '/correlation-station/seca-review'
              }}>
                View SECA Entries
              </Button>
            </div>
          )}

          {/* Error */}
          {stage === 'error' && (
            <div className="space-y-4">
              <div className="p-4 bg-destructive/10 border border-destructive rounded-lg">
                <div className="flex items-center gap-2 text-destructive mb-2">
                  <XCircle className="h-5 w-5" />
                  <span className="font-semibold">Processing Failed</span>
                </div>
                <p className="text-sm">{error || 'An unknown error occurred'}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={handleReset} className="flex-1">
                  Try Again
                </Button>
                <Button variant="outline" onClick={handleClose} className="flex-1">
                  Close
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

