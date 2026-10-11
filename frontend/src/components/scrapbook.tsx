import { useEffect, useState, type HTMLAttributes, type ReactNode } from 'react'

type Tone = 'blue' | 'coral' | 'yellow' | 'neutral'

export function PaperCard({ tone = 'neutral', taped = false, className = '', children, ...props }: HTMLAttributes<HTMLElement> & { tone?: Tone; taped?: boolean; children: ReactNode }) {
  return <article className={`paper-card paper-card--${tone} ${taped ? 'paper-card--taped' : ''} ${className}`} {...props}>{children}</article>
}

export function Shape({ shape = 'circle', tone = 'blue', size = 'md', className = '', label }: { shape?: 'circle' | 'square' | 'star' | 'triangle' | 'arch'; tone?: Tone; size?: 'sm' | 'md' | 'lg'; className?: string; label?: string }) {
  return <span className={`shape shape--${shape} shape--${tone} shape--${size} ${className}`} aria-label={label} aria-hidden={label ? undefined : true} />
}

export function Bulb({ className = '' }: { className?: string }) {
  return <span className={`bulb ${className}`} aria-hidden="true"><i /><b /></span>
}

export function WashiLabel({ children, tone = 'yellow' }: { children: ReactNode; tone?: Tone }) {
  return <span className={`washi washi--${tone}`}>{children}</span>
}

/** Truthful, patient feedback for cold backend starts and page-level queries. */
export function LoadingState({ fullPage = false, label = 'Preparing your plot' }: { fullPage?: boolean; label?: string }) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const started = Date.now()
    const timer = window.setInterval(() => setElapsed(Date.now() - started), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const detail = elapsed < 8_000
    ? 'Warming up your workspace…'
    : elapsed < 30_000
      ? 'The server is taking a little longer than usual. Your request is still on its way.'
      : 'Still connecting. This can take a minute when the service has been resting.'
  return (
    <section className={`loading-state ${fullPage ? 'loading-state--page' : ''}`} role="status" aria-live="polite" aria-label={label}>
      <div className="loading-shapes" aria-hidden="true"><Shape shape="star" tone="yellow" /><Shape shape="square" tone="coral" /><Bulb /></div>
      <div><WashiLabel tone="blue">PlotPlanner</WashiLabel><h2>{label}</h2><p>{detail}</p></div>
      <div className="loading-thread" aria-hidden="true"><i /><i /><i /></div>
    </section>
  )
}
