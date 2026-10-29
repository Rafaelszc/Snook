import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import type { ApiError } from "@/lib/api/errors"
import { postForm } from "@/lib/api/upload"

export interface SendInput {
  file: File
  title: string
  expectedSpeakers: string
}

interface Created {
  id: string
}

// Mesmo `POST /meetings` do upload (`screen-recording`, "Contrato com outros módulos").
function send(
  { file, title, expectedSpeakers }: SendInput,
  onProgress: (fraction: number) => void
): Promise<Created> {
  const form = new FormData()
  form.append("file", file)
  if (title.trim()) form.append("title", title.trim())
  if (expectedSpeakers.trim())
    form.append("expected_speakers", expectedSpeakers.trim())
  return postForm<Created>("/meetings", form, onProgress)
}

export function useSendRecording() {
  const queryClient = useQueryClient()
  const [progress, setProgress] = useState(0)
  const mutation = useMutation<Created, ApiError, SendInput>({
    mutationFn: (input) => {
      setProgress(0)
      return send(input, setProgress)
    },
    // Chave da lista de `meetings`; feature não importa feature.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["meetings"] }),
  })
  return { ...mutation, progress }
}
