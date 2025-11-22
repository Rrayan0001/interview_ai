import * as React from "react"
import { cn } from "../../lib/utils"

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center border-2 border-black px-3 py-1 text-xs font-bold uppercase tracking-wide brutal-shadow",
        {
          "bg-black text-white": variant === "default",
          "bg-white text-black": variant === "secondary",
          "bg-red-500 text-white border-red-600": variant === "destructive",
          "bg-gray-100 text-black border-gray-400": variant === "outline",
        },
        className
      )}
      {...props}
    />
  )
}

export { Badge }