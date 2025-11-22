import * as React from "react"
import { cn } from "../../lib/utils"

export interface ProgressProps
  extends React.HTMLAttributes<HTMLDivElement> {
  value?: number
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "brutal-progress relative h-6 w-full overflow-hidden bg-white",
        className
      )}
      {...props}
    >
      <div
        className="brutal-progress-bar h-full transition-all duration-300"
        style={{ width: `${value || 0}%` }}
      />
    </div>
  )
)
Progress.displayName = "Progress"

export { Progress }