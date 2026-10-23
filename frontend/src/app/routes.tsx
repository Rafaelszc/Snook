import type { RouteObject } from "react-router"

import { LoginPage } from "@/features/auth/LoginPage"
import { RegisterPage } from "@/features/auth/RegisterPage"

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
          { index: true, element: <Placeholder title="Reuniões" /> },
          ...(import.meta.env.DEV
            ? [{ path: "dev/components", element: <SamplePage /> }]
            : []),
          { path: "settings", element: <Placeholder title="Configurações" /> },
          { path: "*", element: <Placeholder title="Página não encontrada" /> },
        ],
      },
    ],
  },
]
