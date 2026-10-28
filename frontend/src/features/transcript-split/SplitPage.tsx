import { ArrowLeft, CircleAlert } from "lucide-react"
import { useEffect } from "react"
import { Link, useNavigate, useParams } from "react-router"

import { Button } from "@/components/ui/button"

import type { SplitState } from "./api"
import { CancelSplitButton } from "./CancelSplitButton"
import { CUTS_HINT_ID } from "./CutControls"
import { MESSAGES, PROVIDER_LABELS } from "./messages"
import { PartSummary } from "./PartSummary"
import { SegmentList } from "./SegmentList"
import { useCuts } from "./useCuts"
import { useConfirmSplit, useSplit } from "./useSplit"

const ALERT =
  "rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"

const detailPath = (meetingId: string) => `/meetings/${meetingId}`

// Sem provedor ativo: só a mensagem e o caminho para as configurações (`transcript-split` 44).
function NoProvider({ message }: { message: string }) {
  return (
    <div role="alert" className={`flex flex-col gap-2 ${ALERT}`}>
      <p className="flex items-start gap-2">
        <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        {message}
      </p>
      <Link
        to="/settings"
        className="self-start font-medium underline underline-offset-4"
      >
        {MESSAGES.openSettings}
      </Link>
    </div>
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
      <section className="flex flex-col gap-2">
        <p className="text-base">
          {MESSAGES.why(split.total_tokens ?? 0, budget)}
        </p>
        {split.split_reason === "adjust" ? (
          <p className="text-sm text-muted-foreground">{MESSAGES.adjust}</p>
        ) : null}
        <p className="text-sm text-muted-foreground">
          {MESSAGES.providerUsed(provider, split.model ?? "")}{" "}
          <Link
            to="/settings"
            className="font-medium text-foreground underline underline-offset-4"
          >
            {MESSAGES.changeModel}
          </Link>
        </p>
      </section>
      <p id={CUTS_HINT_ID} className="text-sm text-muted-foreground">
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
        <h2 className="text-sm font-medium">{MESSAGES.partsLabel}</h2>
        <PartSummary parts={parts} />
      </section>
      {confirm.error ? (
        <p role="alert" className={ALERT}>
          {confirm.error.message}
        </p>
      ) : null}
      <div className="flex flex-wrap items-start gap-x-4 gap-y-3 border-t border-border pt-5">
        <Button
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
          className="min-h-9 flex-1 py-2 text-sm text-muted-foreground"
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
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 py-4">
      <Link
        to={detailPath(id)}
        className="inline-flex items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      <h1 className="text-2xl font-semibold">{MESSAGES.title}</h1>
      {error ? (
        error.status === 409 ? (
          <p className="text-sm text-muted-foreground">
            {MESSAGES.notAvailable}
          </p>
        ) : (
          <p role="alert" className={ALERT}>
            {error.status === 404 ? MESSAGES.notFound : error.message}
          </p>
        )
      ) : !split || started ? (
        <div aria-busy="true" className="flex flex-col gap-3">
          <span role="status" className="sr-only">
            {MESSAGES.loading}
          </span>
          <div className="h-16 rounded-xl bg-muted" />
          <div className="h-64 rounded-xl bg-muted" />
        </div>
      ) : split.message ? (
        <NoProvider message={split.message} />
      ) : (
        <SplitEditor meetingId={id} split={split} />
      )}
    </div>
  )
}
