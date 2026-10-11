import type { HTMLAttributes, ReactNode } from 'react'

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
