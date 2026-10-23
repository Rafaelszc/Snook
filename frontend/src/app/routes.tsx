import type { RouteObject } from "react-router"

import { RegisterPage } from "@/features/auth/RegisterPage"

import { Layout } from "./Layout"
import { SamplePage } from "./SamplePage"

function Placeholder({ title }: { title: string }) {
  return <h1>{title}</h1>
}

// Telas reais entram nas tasks de cada módulo; guarda de rota vem na Task 10.2.
export const routes: RouteObject[] = [
  { path: "/login", element: <Placeholder title="Entrar" /> },
  { path: "/register", element: <RegisterPage /> },
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
]
