import { ArrowLeft } from "lucide-react"
import { useEffect } from "react"
import { Link, useNavigate, useParams } from "react-router"

import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
import { Skeleton, SkeletonGroup } from "@/components/surfaces/Skeleton"
import { Button } from "@/components/ui/button"

import type { SplitState } from "./api"
import { CancelSplitButton } from "./CancelSplitButton"
import { CUTS_HINT_ID } from "./CutControls"
import { MESSAGES, PROVIDER_LABELS } from "./messages"
import { PartSummary } from "./PartSummary"
import { SegmentList } from "./SegmentList"
import { useCuts } from "./useCuts"
import { useConfirmSplit, useSplit } from "./useSplit"

const detailPath = (meetingId: string) => `/meetings/${meetingId}`

// Sem provedor ativo: só a mensagem e o caminho para as configurações (`transcript-split` 44).
function NoProvider({ message }: { message: string }) {
  return (
    <Notice variant="warn" role="alert">
      <div className="flex flex-col gap-2">
        <p>{message}</p>
        <Link
          to="/settings"
          className="self-start rounded-sm font-medium text-ink underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {MESSAGES.openSettings}
        </Link>
      </div>
    </Notice>
  )
}

function SplitEditor({
  meetingId,
  split,
}: {
  meetingId: string
  split: SplitState
}) {
  const navigate = useNavigate()
  const budget = split.budget ?? 0
  const { cuts, parts, cutIds, allFit, toggle, move } = useCuts(
    split.segments,
    split.cuts,
    budget
  )
  const confirm = useConfirmSplit(meetingId)
  const over = parts.filter((part) => !part.fits).length
  const provider = split.provider
    ? (PROVIDER_LABELS[split.provider] ?? split.provider)
    : ""

  return (
    <div className="flex flex-col gap-6">
      <section className="flex max-w-reading flex-col gap-2">
        <p className="font-serif text-base text-ink">
          {MESSAGES.why(split.total_tokens ?? 0, budget)}
        </p>
        {split.split_reason === "adjust" ? (
          <p className="text-sm text-ink-muted">{MESSAGES.adjust}</p>
        ) : null}
        <p className="text-sm text-ink-muted">
          {MESSAGES.providerUsed(provider, split.model ?? "")}{" "}
          <Link
            to="/settings"
            className="rounded-sm font-medium text-ink underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {MESSAGES.changeModel}
          </Link>
        </p>
      </section>
      <p id={CUTS_HINT_ID} className="text-sm text-ink-muted">
        {MESSAGES.cutsHint}
      </p>
      <SegmentList
        segments={split.segments}
        cuts={cuts}
        disabled={confirm.isPending}
        onToggle={toggle}
        onMove={move}
      />
      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-medium text-ink">{MESSAGES.partsLabel}</h2>
        <PartSummary parts={parts} />
      </section>
      {confirm.error ? (
        <Notice variant="error">{confirm.error.message}</Notice>
      ) : null}
      <div className="flex flex-wrap items-start gap-x-4 gap-y-3 border-t border-ink pt-4">
        <Button
          variant="accent"
          disabled={!allFit || confirm.isPending}
          aria-describedby="split-status"
          onClick={() =>
            confirm.mutate(cutIds, {
              onSuccess: () => navigate(detailPath(meetingId)),
            })
          }
        >
          {confirm.isPending ? MESSAGES.confirming : MESSAGES.confirm}
        </Button>
        <p
          id="split-status"
          aria-live="polite"
          className="min-h-9 flex-1 py-2 text-sm text-ink-muted"
        >
          {MESSAGES.summary(parts.length, over)}
        </p>
        {split.can_cancel ? (
          <CancelSplitButton
            meetingId={meetingId}
            disabled={confirm.isPending}
          />
        ) : null}
      </div>
    </div>
  )
}

// Tamanhos de texto: sm, base, 2xl.
export function SplitPage() {
  const { id = "" } = useParams()
  const navigate = useNavigate()
  const { data: split, error } = useSplit(id)
  // Passou a caber no `refresh`: segue para a geração sem mostrar cortes (`transcript-split` 47).
  const started = split !== undefined && split.status !== "needs_split"

  useEffect(() => {
    if (started) navigate(detailPath(id), { replace: true })
  }, [started, id, navigate])

  return (
    <div className="flex flex-col gap-6">
      <Link
        to={detailPath(id)}
        className="inline-flex items-center gap-2 self-start rounded-sm text-sm text-ink-muted outline-none hover:text-ink focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      <PageHeader title={MESSAGES.title} />
      {error ? (
        error.status === 409 ? (
          <p className="text-sm text-ink-muted">{MESSAGES.notAvailable}</p>
        ) : (
          <Notice variant="error">
            {error.status === 404 ? MESSAGES.notFound : error.message}
          </Notice>
        )
      ) : !split || started ? (
        <SkeletonGroup label={MESSAGES.loading}>
          <Skeleton className="h-16" />
          <Skeleton className="h-64" />
        </SkeletonGroup>
      ) : split.message ? (
        <NoProvider message={split.message} />
      ) : (
        <SplitEditor meetingId={id} split={split} />
      )}
    </div>
  )
}
