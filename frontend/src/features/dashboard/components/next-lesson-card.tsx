import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Compass } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import type { DashboardNextLesson } from "@/features/dashboard/types/dashboard"

export interface NextLessonCardProps {
  nextLesson: DashboardNextLesson | null
}

export function NextLessonCard({ nextLesson }: NextLessonCardProps) {
  const { t } = useTranslation()
  const [showComingSoon, setShowComingSoon] = useState(false)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Compass className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.nextLesson.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {nextLesson === null ? (
          <span className="text-sm text-muted-foreground">{t("dashboard.nextLesson.empty")}</span>
        ) : (
          <>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {nextLesson.track_title}
              </span>
              <span className="text-lg font-medium text-foreground">{nextLesson.lesson_title}</span>
            </div>
            <Button onClick={() => setShowComingSoon(true)} className="w-fit">
              {t("dashboard.nextLesson.cta")}
            </Button>
            {showComingSoon && (
              <p role="status" className="text-xs text-muted-foreground">
                {t("dashboard.nextLesson.comingSoon")}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
