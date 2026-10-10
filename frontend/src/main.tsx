import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './app/AuthProvider'
import { ConfigError, getEnv } from './lib/env'
import './index.css'

const queryClient = new QueryClient()
const root = createRoot(document.getElementById('root')!)

function renderConfigError(message: string) {
  root.render(
    <div className="app">
      <section className="panel auth-card">
        <header className="panel-header">
          <h1 className="brand small">PlotPlanner</h1>
          <p>The frontend is not configured.</p>
        </header>
        <p className="toast err" role="alert">
          {message}
        </p>
      </section>
    </div>,
  )
}

try {
  getEnv()
  root.render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  )
} catch (error) {
  if (!(error instanceof ConfigError)) throw error
  renderConfigError(error.message)
}
