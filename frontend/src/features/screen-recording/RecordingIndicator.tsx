// Pulso discreto; fixo com movimento reduzido (ADR-0024, motion.css).
export function RecordingIndicator() {
  return (
    <span
      aria-hidden="true"
      data-testid="recording-indicator"
      className="motion-pulse inline-block size-2.5 shrink-0 rounded-full bg-failed"
    />
  )
}
