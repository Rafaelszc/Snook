import { useState, type ChangeEvent, type FormEvent } from "react"
import { Link, useNavigate } from "react-router"

import { FormField } from "@/components/forms/FormField"
import { Button } from "@/components/ui/button"

import { AuthShell } from "./AuthShell"
import { useRegister } from "./useRegister"

const EMPTY = { email: "", username: "", password: "" }

export function RegisterPage() {
  const navigate = useNavigate()
  const register = useRegister()
  const [form, setForm] = useState(EMPTY)

  const fields = register.error?.fields ?? {}
  // Erro sem campo (409, rede) vai no alerta geral; com campo, sob o campo.
  const generalError =
    register.error && Object.keys(fields).length === 0
      ? register.error.message
      : undefined

  function update(name: keyof typeof EMPTY) {
    return (event: ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [name]: event.target.value }))
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    register.mutate(form, {
      onSuccess: () => navigate("/", { replace: true }),
    })
  }

  return (
    <AuthShell
      title="Criar conta"
      description="Transcreva reuniões e gere backlog na sua máquina."
    >
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        <div role="alert" aria-live="assertive" className="empty:hidden">
          {generalError ? (
            <p className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {generalError}
            </p>
          ) : null}
        </div>
        <FormField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          spellCheck={false}
          required
          value={form.email}
          onChange={update("email")}
          error={fields.email}
        />
        <FormField
          label="Nome de usuário"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          value={form.username}
          onChange={update("username")}
          hint="3 a 30 caracteres: letras, dígitos, _, . e -"
          error={fields.username}
        />
        <FormField
          label="Senha"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          value={form.password}
          onChange={update("password")}
          hint="8 caracteres ou mais"
          error={fields.password}
        />
        <Button
          type="submit"
          size="lg"
          className="mt-2 h-10"
          disabled={register.isPending}
        >
          {register.isPending ? "Criando conta…" : "Criar conta"}
        </Button>
      </form>
      <p className="text-sm text-muted-foreground">
        Já tem conta?{" "}
        <Link
          to="/login"
          className="font-medium text-foreground underline underline-offset-4"
        >
          Entrar
        </Link>
      </p>
    </AuthShell>
  )
}
