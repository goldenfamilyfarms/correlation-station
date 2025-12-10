interface ErrorResponse {
  service: string
  route: string
  correlationId?: string
  status: number
  message: string
}

class HttpClient {
  private baseURL: string

  constructor(baseURL: string = '') {
    this.baseURL = baseURL
  }

  private async handleResponse(response: Response, route: string): Promise<any> {
    if (!response.ok) {
      const contentType = response.headers.get('content-type')
      
      // Detect 502/404 with HTML response instead of JSON
      if (contentType?.includes('text/html')) {
        throw {
          service: this.extractServiceName(route),
          route,
          status: response.status,
          message: response.status === 502 
            ? 'Bad Gateway - Service unavailable' 
            : 'Not Found - Invalid endpoint',
          correlationId: response.headers.get('x-correlation-id') || undefined
        } as ErrorResponse
      }

      const error = await response.json().catch(() => ({ message: response.statusText }))
      throw {
        service: this.extractServiceName(route),
        route,
        status: response.status,
        message: error.message || response.statusText,
        correlationId: response.headers.get('x-correlation-id') || undefined
      } as ErrorResponse
    }

    return response.json()
  }

  private extractServiceName(route: string): string {
    if (route.includes('correlation-engine')) return 'Correlation Engine'
    if (route.includes('arda')) return 'ARDA'
    if (route.includes('grafana')) return 'Grafana'
    if (route.includes('pyroscope')) return 'Pyroscope'
    return 'Unknown Service'
  }

  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${path}`)
    return this.handleResponse(response, path)
  }

  async post<T>(path: string, data: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return this.handleResponse(response, path)
  }
}

export const httpClient = new HttpClient()
export type { ErrorResponse }
