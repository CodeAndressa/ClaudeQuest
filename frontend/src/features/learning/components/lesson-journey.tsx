import { Beaker, Check, ClipboardCheck, FileText, GitBranch, PenLine } from "lucide-react"
import { Link } from "react-router"
import { useTranslation } from "react-i18next"

import type { TrackDetail } from "@/features/learning/types/learning"
import { cn } from "@/lib/utils"

const TYPE_ICONS = {
  lab: Beaker,
  checklist: ClipboardCheck,
  free_answer: PenLine,
  challenge: GitBranch,
  reading: FileText,
  quiz: FileText,
  upload: FileText,
} as const

export function LessonJourney({
  track,
  currentLessonId,
}: {
  track: TrackDetail
  currentLessonId: string
}) {
  const { t } = useTranslation()
  const activeModule = track.modules.find((module) =>
    module.levels.some((level) => level.lessons.some((lesson) => lesson.id === currentLessonId))
  )
  const lessons = activeModule?.levels.flatMap((level) => level.lessons) ?? []

  return (
    <aside className="hidden min-h-[calc(100vh-81px)] border-r border-border bg-[#050a08] px-5 py-7 lg:block">
      <div className="mb-6 flex items-center gap-2">
        <span className="flex size-6 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Check className="size-4" aria-hidden="true" />
        </span>
        <h2 className="font-medium text-foreground">{activeModule?.title ?? track.title}</h2>
      </div>
      <ol className="relative ml-3 flex flex-col gap-3 border-l border-primary/50 pl-5">
        {lessons.map((lesson) => {
          const Icon = TYPE_ICONS[lesson.lesson_type as keyof typeof TYPE_ICONS] ?? FileText
          const current = lesson.id === currentLessonId
          return (
            <li key={lesson.id} className="relative">
              <span
                className={cn(
                  "absolute -left-[26px] top-5 size-2 rounded-full",
                  lesson.completed || current ? "bg-primary shadow-[0_0_10px_#34d399]" : "bg-border"
                )}
                aria-hidden="true"
              />
              <Link
                to={`/tracks/${track.id}/lessons/${lesson.id}`}
                aria-current={current ? "step" : undefined}
                className={cn(
                  "flex min-h-16 items-center gap-3 rounded-md border px-3 py-3 transition-colors",
                  current
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card/40 hover:border-primary/40"
                )}
              >
                <Icon
                  className={cn(
                    "size-5 shrink-0",
                    current ? "text-primary" : "text-muted-foreground"
                  )}
                  aria-hidden="true"
                />
                <span className="min-w-0">
                  <span className="block text-xs text-primary">
                    {t(`lesson.type.${lesson.lesson_type}`, { defaultValue: lesson.lesson_type })}
                  </span>
                  <span className="mt-0.5 block line-clamp-2 text-sm text-foreground">
                    {lesson.title}
                  </span>
                </span>
                {lesson.completed ? (
                  <Check className="ml-auto size-4 shrink-0 text-primary" aria-hidden="true" />
                ) : null}
              </Link>
            </li>
          )
        })}
      </ol>
    </aside>
  )
}
