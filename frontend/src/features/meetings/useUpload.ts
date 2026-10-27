import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import type { ApiError } from "@/lib/api/errors"
import { postForm } from "@/lib/api/upload"

import { meetingsQueryKey, type MeetingSummary } from "./api"

export interface UploadInput {
  file: File
  title: string
  expectedSpeakers: string
}

function send(
  { file, title, expectedSpeakers }: UploadInput,
  onProgress: (fraction: number) => void
): Promise<MeetingSummary> {
  const form = new FormData()
  form.append("file", file)
  if (title.trim()) form.append("title", title.trim())
  if (expectedSpeakers.trim())
    form.append("expected_speakers", expectedSpeakers.trim())
  return postForm<MeetingSummary>("/meetings", form, onProgress)
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
