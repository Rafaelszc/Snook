import { NavLink, Outlet } from "react-router"

const links = [
  { to: "/", label: "Reuniões" },
  { to: "/settings", label: "Configurações" },
]

export function Layout() {
  return (
    <div className="min-h-svh">
      <header>
        <nav aria-label="Principal" className="flex gap-4 p-4">
          {links.map(({ to, label }) => (
            <NavLink key={to} to={to} end>
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="p-4">
        <Outlet />
      </main>
    </div>
  )
}
