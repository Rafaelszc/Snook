import type { RouteObject } from "react-router"

import { LoginPage } from "@/features/auth/LoginPage"
import { RegisterPage } from "@/features/auth/RegisterPage"
import { TranscriptPage } from "@/features/diarized-transcription/TranscriptPage"
import { SettingsPage } from "@/features/llm-providers/SettingsPage"
import { MeetingDetailPage } from "@/features/meetings/MeetingDetailPage"
import { MeetingListPage } from "@/features/meetings/MeetingListPage"
import { UploadPage } from "@/features/meetings/UploadPage"

import { AuthGuard } from "./AuthGuard"
import { Layout } from "./Layout"
import { SamplePage } from "./SamplePage"

function Placeholder({ title }: { title: string }) {
  return <h1>{title}</h1>
}

// Telas reais entram nas tasks de cada módulo.
export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <AuthGuard />,
    children: [
      {
        element: <Layout />,
        children: [
          { index: true, element: <MeetingListPage /> },
          { path: "meetings/new", element: <UploadPage /> },
          { path: "meetings/:id", element: <MeetingDetailPage /> },
          { path: "meetings/:id/transcript", element: <TranscriptPage /> },
          ...(import.meta.env.DEV
            ? [{ path: "dev/components", element: <SamplePage /> }]
            : []),
          { path: "settings", element: <SettingsPage /> },
          { path: "*", element: <Placeholder title="Página não encontrada" /> },
        ],
      },
    ],
  },
]
