import type { RouteObject } from "react-router"

import { Layout } from "./Layout"

function Placeholder({ title }: { title: string }) {
  return <h1>{title}</h1>
}

// Telas reais entram nas tasks de cada módulo; guarda de rota vem na Task 10.2.
export const routes: RouteObject[] = [
  { path: "/login", element: <Placeholder title="Entrar" /> },
  { path: "/register", element: <Placeholder title="Cadastro" /> },
  {
    element: <Layout />,
    children: [
      { index: true, element: <Placeholder title="Reuniões" /> },
      { path: "settings", element: <Placeholder title="Configurações" /> },
      { path: "*", element: <Placeholder title="Página não encontrada" /> },
    ],
  },
]
