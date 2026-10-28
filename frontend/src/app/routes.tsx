import type { RouteObject } from "react-router"

import { LoginPage } from "@/features/auth/LoginPage"
import { RegisterPage } from "@/features/auth/RegisterPage"
import { TranscriptPage } from "@/features/diarized-transcription/TranscriptPage"
import { SettingsPage } from "@/features/llm-providers/SettingsPage"
import { MeetingDetailPage } from "@/features/meetings/MeetingDetailPage"
import { MeetingListPage } from "@/features/meetings/MeetingListPage"
import { UploadPage } from "@/features/meetings/UploadPage"
import { NamingPage } from "@/features/participants/NamingPage"
import { RecordPage } from "@/features/screen-recording/RecordPage"
import { SplitPage } from "@/features/transcript-split/SplitPage"

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
          { path: "meetings/record", element: <RecordPage /> },
          { path: "meetings/:id", element: <MeetingDetailPage /> },
          { path: "meetings/:id/transcript", element: <TranscriptPage /> },
          { path: "meetings/:id/participants", element: <NamingPage /> },
          { path: "meetings/:id/split", element: <SplitPage /> },
          // Destino de "Cancelar divisão"; a tela real entra na Task 49.1.
          {
            path: "meetings/:id/backlog",
            element: <Placeholder title="Revisão do backlog" />,
          },
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
