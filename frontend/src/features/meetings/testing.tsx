import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import { createMemoryRouter, RouterProvider } from "react-router"

import { MeetingDetailPage } from "./MeetingDetailPage"
import { MeetingListPage } from "./MeetingListPage"
import { UploadPage } from "./UploadPage"

// Rotas mínimas da feature; a página de destino só mostra o caminho.
export function renderMeetings(path: string) {
  const router = createMemoryRouter(
    [
      { path: "/", element: <MeetingListPage /> },
      { path: "/meetings/new", element: <UploadPage /> },
      { path: "/meetings/:id", element: <MeetingDetailPage /> },
    ],
    { initialEntries: [path] }
  )
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
  return { ...view, router }
}
