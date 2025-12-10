import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CodeBlockProps {
  code: string
  language?: string
}

export default function CodeBlock({ code, language = 'text' }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const highlightCode = (text: string, lang: string) => {
    const keywords = {
      logql: ['sum', 'count_over_time', 'rate', 'avg_over_time', 'json', 'logfmt', 'unwrap'],
      traceql: ['duration', 'status', 'error', 'service', 'name'],
      python: ['from', 'import', 'def', 'class', 'return', 'async', 'await', 'with', 'as'],
      yaml: ['version', 'services', 'environment', 'ports', 'volumes'],
    }

    const langKeywords = keywords[lang as keyof typeof keywords] || []
    let highlighted = text

    // Highlight keywords in orange
    langKeywords.forEach(keyword => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'g')
      highlighted = highlighted.replace(regex, `<span class="text-grafana-orange font-semibold">${keyword}</span>`)
    })

    // Highlight strings in white
    highlighted = highlighted.replace(/"([^"]*)"/g, '<span class="text-white">"$1"</span>')
    highlighted = highlighted.replace(/'([^']*)'/g, "<span class=\"text-white\">'$1'</span>")

    // Highlight operators
    highlighted = highlighted.replace(/([|=><&!+\-*\/])/g, '<span class="text-grafana-yellow">$1</span>')

    // Highlight numbers
    highlighted = highlighted.replace(/\b(\d+)\b/g, '<span class="text-grafana-blue">$1</span>')

    return highlighted
  }

  return (
    <div className="relative group my-4">
      <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCopy}
          className="h-8 px-2 bg-gray-800 hover:bg-gray-700 text-white"
        >
          {copied ? (
            <>
              <Check className="h-4 w-4 mr-1" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-4 w-4 mr-1" />
              Copy
            </>
          )}
        </Button>
      </div>
      <pre className="bg-black rounded-lg p-4 overflow-x-auto border border-gray-700">
        <code
          className="text-gray-300 text-sm font-mono"
          dangerouslySetInnerHTML={{ __html: highlightCode(code, language) }}
        />
      </pre>
    </div>
  )
}
