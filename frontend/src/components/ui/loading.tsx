import { Loader2 } from "lucide-react"
import { cn } from "../../lib/utils"

interface LoadingOverlayProps {
  text?: string
  className?: string
}

export function LoadingOverlay({ text = "Loading...", className }: LoadingOverlayProps) {
  return (
    <div className={cn(
      "fixed inset-0 z-50 flex items-center justify-center bg-white/90",
      className
    )}>
      <div className="brutal-card brutal-shadow-xl p-12 text-center">
        <div className="brutal-border brutal-shadow-lg p-6 bg-black mb-6 mx-auto w-fit">
          <Loader2 className="h-16 w-16 animate-spin text-white" />
        </div>
        <p className="text-2xl font-black uppercase tracking-wider">{text}</p>
        <div className="brutal-border brutal-shadow bg-yellow-300 p-2 mt-4">
          <p className="text-sm font-bold uppercase">PLEASE WAIT...</p>
        </div>
      </div>
    </div>
  )
}

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg"
  className?: string
}

export function LoadingSpinner({ size = "md", className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6", 
    lg: "h-8 w-8"
  }

  return (
    <Loader2 className={cn(
      "animate-spin text-primary",
      sizeClasses[size],
      className
    )} />
  )
}