import { useState, type ChangeEvent, type FormEvent } from "react"
import { Link, useLocation, useNavigate } from "react-router"

import { Button } from "@/components/ui/button"

import { AuthShell } from "./AuthShell"
import { FormField } from "./FormField"
import { useLogin } from "./useSession"

const EMPTY = { identifier: "", password: "" }

// Só caminho interno: `//host` ou URL absoluta viraria redirecionamento aberto.
function returnPath(state: unknown): string {
  const from = (state as { from?: unknown } | null)?.from
  return typeof from === "string" &&
    from.startsWith("/") &&
    !from.startsWith("//")
    ? from
    : "/"
}

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useLogin()
  const [form, setForm] = useState(EMPTY)

  function update(name: keyof typeof EMPTY) {
    return (event: ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [name]: event.target.value }))
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    login.mutate(form, {
      onSuccess: () => navigate(returnPath(location.state), { replace: true }),
    })
  }

  return (
    <AuthShell title="Entrar" description="Acesse suas reuniões e backlogs.">
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        {/* Falha de login é sempre genérica (SEC-05): alerta geral, não por campo. */}
        <div role="alert" aria-live="assertive" className="empty:hidden">
          {login.error ? (
            <p className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {login.error.message}
            </p>
          ) : null}
        </div>
        <FormField
          label="Email ou nome de usuário"
          name="identifier"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          value={form.identifier}
          onChange={update("identifier")}
        />
        <FormField
          label="Senha"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={form.password}
          onChange={update("password")}
        />
        <Button
          type="submit"
          size="lg"
          className="mt-2 h-10"
          disabled={login.isPending}
        >
          {login.isPending ? "Entrando…" : "Entrar"}
        </Button>
      </form>
      <p className="text-sm text-muted-foreground">
        Não tem conta?{" "}
        <Link
          to="/register"
          className="font-medium text-foreground underline underline-offset-4"
        >
          Criar conta
        </Link>
      </p>
    </AuthShell>
  )
}
