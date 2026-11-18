import type { ReactNode } from 'react'

export function Loading({ label = 'Loading' }: { label?: string }) {
  return <p className="status" role="status">{label}…</p>
}

export function ErrorNotice({ error }: { error: Error }) {
  return (
    <div className="notice notice--error" role="alert">
      <strong>Couldn't load this.</strong> {error.message}
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <p className="empty__title">{title}</p>
      {children}
    </div>
  )
}
