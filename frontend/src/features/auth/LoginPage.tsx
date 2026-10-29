import { useState, type ChangeEvent, type FormEvent } from "react"
import { Link, useLocation, useNavigate } from "react-router"

import { FormField } from "@/components/forms/FormField"
import { Notice } from "@/components/surfaces/Notice"
import { Button } from "@/components/ui/button"

import { AuthShell } from "./AuthShell"
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
        {/* role="alert" do Notice error já é região viva assertiva; aria-live explícito reforça. */}
        {login.error ? (
          <Notice variant="error" aria-live="assertive">
            {login.error.message}
          </Notice>
        ) : null}
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
          variant="accent"
          className="mt-2"
          disabled={login.isPending}
        >
          {login.isPending ? "Entrando…" : "Entrar"}
        </Button>
      </form>
      <p className="text-sm text-ink-muted">
        Não tem conta?{" "}
        <Link
          to="/register"
          className="rounded-sm font-medium text-ink underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Criar conta
        </Link>
      </p>
    </AuthShell>
  )
}
