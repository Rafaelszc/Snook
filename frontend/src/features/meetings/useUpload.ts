import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { ApiError, parseApiError } from "@/lib/api/errors"

import { meetingsQueryKey, type MeetingSummary } from "./api"

export interface UploadInput {
  file: File
  title: string
  expectedSpeakers: string
}

// fetch não informa progresso de envio; XHR sim (`meetings` 35). Cookie vai por mesma origem.
function send(
  { file, title, expectedSpeakers }: UploadInput,
  onProgress: (fraction: number) => void
): Promise<MeetingSummary> {
  const form = new FormData()
  form.append("file", file)
  if (title.trim()) form.append("title", title.trim())
  if (expectedSpeakers.trim())
    form.append("expected_speakers", expectedSpeakers.trim())

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", "/api/meetings")
    xhr.setRequestHeader("Accept", "application/json")
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && e.total > 0) onProgress(e.loaded / e.total)
    }
    xhr.onload = () => {
      const response = new Response(xhr.responseText || null, {
        status: xhr.status,
      })
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText) as MeetingSummary)
        return
      }
      parseApiError(response).then(reject, reject)
    }
    xhr.onerror = () =>
      reject(new ApiError(0, "network_error", "Sem conexão com o servidor."))
    xhr.send(form)
  })
}

export function useUpload() {
  const queryClient = useQueryClient()
  const [progress, setProgress] = useState(0)
  const mutation = useMutation<MeetingSummary, ApiError, UploadInput>({
    mutationFn: (input) => {
      setProgress(0)
      return send(input, setProgress)
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: meetingsQueryKey }),
  })
  return { ...mutation, progress }
}
