import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react"
import { cn } from "cn"

import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"

import { THEME_LABELS } from "./messages"

const OPTIONS: { value: "light" | "dark" | "system"; icon: LucideIcon }[] = [
  { value: "light", icon: Sun },
  { value: "dark", icon: Moon },
  { value: "system", icon: Monitor },
]

// Controle visível de tema (ADR-0024, "Tema"); sem atalho de tecla.
function ThemeToggle({
  className,
  ...props
}: Omit<React.ComponentProps<"div">, "children" | "role">) {
  const { theme, setTheme } = useTheme()

  return (
    <div
      role="group"
      aria-label={THEME_LABELS.group}
      className={cn("inline-flex items-center gap-1", className)}
      {...props}
    >
      {OPTIONS.map(({ value, icon: Icon }) => (
        <Button
          key={value}
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-pressed={theme === value}
          aria-label={THEME_LABELS[value]}
          title={THEME_LABELS[value]}
          className="aria-pressed:bg-sunken aria-pressed:text-signal"
          onClick={() => setTheme(value)}
        >
          <Icon aria-hidden="true" />
        </Button>
      ))}
    </div>
  )
}

export { ThemeToggle }
