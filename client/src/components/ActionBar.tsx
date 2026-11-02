export type BusyAction = 'run' | 'reset' | null

interface ActionBarProps {
  busy: BusyAction
  onRun: () => void
  onReset: () => void
}

export function ActionBar({ busy, onRun, onReset }: ActionBarProps) {
  const disabled = busy !== null
  return (
    <div className="action-bar">
      <button type="button" className="btn btn--secondary" onClick={onReset} disabled={disabled}>
        {busy === 'reset' ? 'Resetting…' : 'Reset'}
      </button>
      <button type="button" className="btn btn--primary" onClick={onRun} disabled={disabled}>
        {busy === 'run' && <span className="btn__spinner" aria-hidden="true" />}
        {busy === 'run' ? 'Running…' : 'Run process'}
      </button>
    </div>
  )
}
