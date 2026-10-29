import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

// ADR-0024, "Componentes": cinco variantes; accent só no passo que avança o fluxo.
const primary = "bg-primary text-primary-foreground hover:bg-primary/90"
const secondary =
  "border-input bg-transparent text-ink hover:bg-sunken aria-expanded:bg-sunken"
const danger = "border-failed bg-transparent text-failed hover:bg-failed-soft"
const sizeDefault = "h-9 gap-2 px-4"
const sizeSm = "h-8 gap-2 px-3"

const buttonVariants = cva(
  "group/button duration-fast inline-flex shrink-0 items-center justify-center rounded-md border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-transform ease-standard outline-none select-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-failed [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        primary,
        accent: "bg-signal text-signal-ink hover:bg-signal/90",
        secondary,
        ghost: "text-ink hover:bg-sunken aria-expanded:bg-sunken",
        danger,
        // Transitórios: saem na Task 52.9.
        default: primary,
        outline: secondary,
        destructive: danger,
      },
      size: {
        default: sizeDefault,
        sm: sizeSm,
        icon: "size-9",
        "icon-sm": "size-8",
        // Transitórios: saem na Task 52.9.
        xs: sizeSm,
        lg: sizeDefault,
        "icon-xs": "size-8",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "primary",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
