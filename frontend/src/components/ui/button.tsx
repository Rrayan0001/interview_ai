import * as React from "react"
import { cn } from "../../lib/utils"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
  size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        className={cn(
          "brutal-btn inline-flex items-center justify-center whitespace-nowrap font-bold text-sm uppercase tracking-wide disabled:pointer-events-none disabled:opacity-50",
          {
            "brutal-btn-primary": variant === "default",
            "bg-red-500 text-white border-red-600": variant === "destructive",
            "bg-white text-black": variant === "outline",
            "bg-gray-200 text-black": variant === "secondary",
            "bg-transparent border-transparent shadow-none hover:bg-gray-100": variant === "ghost",
            "bg-transparent border-transparent shadow-none text-black underline hover:no-underline": variant === "link",
          },
          {
            "h-12 px-6 py-3": size === "default",
            "h-10 px-4 py-2": size === "sm",
            "h-14 px-8 py-4 text-lg": size === "lg",
            "h-12 w-12": size === "icon",
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }