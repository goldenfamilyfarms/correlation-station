import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface CodeBlockProps {
  code: string
  language?: string
}

// Map custom language names to standard ones
const languageMap: Record<string, string> = {
  logql: 'logql',
  traceql: 'traceql',
  promql: 'promql',
  python: 'python',
  yaml: 'yaml',
  json: 'json',
  bash: 'bash',
  shell: 'bash',
  javascript: 'javascript',
  typescript: 'typescript',
  text: 'text',
}

export default function CodeBlock({ code, language = 'text' }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const mappedLanguage = languageMap[language.toLowerCase()] || language.toLowerCase()

  return (
    <Card className="my-4 overflow-hidden border border-gray-800/50 shadow-lg hover:shadow-xl transition-all duration-300 group">
      <CardHeader className="flex flex-row items-center justify-between bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 py-3 px-4 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
            <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
          </div>
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-2">
            {language}
          </span>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCopy}
          className="h-8 px-3 hover:bg-gray-700/50 text-gray-300 hover:text-white transition-all duration-200 group/copy"
        >
          {copied ? (
            <>
              <Check className="h-4 w-4 mr-1.5 text-green-400" />
              <span className="text-xs font-medium">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-4 w-4 mr-1.5 group-hover/copy:scale-110 transition-transform" />
              <span className="text-xs font-medium">Copy</span>
            </>
          )}
        </Button>
      </CardHeader>
      <CardContent className="p-0 relative overflow-hidden">
        <div className="relative">
          <SyntaxHighlighter
            language={mappedLanguage}
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              padding: '1.25rem',
              background: '#0d1117',
              fontSize: '0.875rem',
              lineHeight: '1.6',
              borderRadius: 0,
            }}
            showLineNumbers={code.split('\n').length > 3}
            lineNumberStyle={{
              minWidth: '3em',
              paddingRight: '1em',
              color: '#6e7681',
              userSelect: 'none',
            }}
            wrapLines={true}
            wrapLongLines={true}
          >
            {code}
          </SyntaxHighlighter>
          {/* Gradient overlay on hover */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        </div>
      </CardContent>
    </Card>
  )
}
