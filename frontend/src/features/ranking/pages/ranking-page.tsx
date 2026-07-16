import { useQuery } from "@tanstack/react-query"
import { Crown, Medal, Trophy } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { fetchRanking } from "@/features/dashboard/services/gamification-service"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/auth-store"

const PODIUM_STYLES = ["text-amber-400", "text-slate-300", "text-amber-700"]

export function RankingPage() {
  const { t } = useTranslation()
  const currentUserId = useAuthStore((state) => state.user?.id)
  const { data, isLoading, isError } = useQuery({
    queryKey: ["gamification", "ranking"],
    queryFn: fetchRanking,
  })

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-8">
      <header className="max-w-3xl">
        <div className="mb-2 flex items-center gap-2 text-primary">
          <Trophy className="size-5" aria-hidden="true" />
          <span className="text-sm font-medium">{t("ranking.global")}</span>
        </div>
        <h1 className="text-2xl font-semibold text-foreground">{t("ranking.title")}</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{t("ranking.subtitle")}</p>
      </header>

      {isLoading ? (
        <div className="flex flex-col gap-2" role="status" aria-label={t("ranking.loading")}>
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      ) : null}

      {isError ? <p className="text-sm text-destructive">{t("ranking.error")}</p> : null}

      {data ? (
        <>
          {data.current_user ? (
            <Card>
              <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
                <div>
                  <p className="text-sm text-muted-foreground">{t("ranking.yourPosition")}</p>
                  <p className="mt-1 text-lg font-semibold text-foreground">
                    {t("ranking.positionOf", {
                      position: data.current_user.position,
                      total: data.total_users,
                    })}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-semibold text-primary">{data.current_user.score}</p>
                  <p className="text-xs text-muted-foreground">{t("ranking.points")}</p>
                </div>
              </CardContent>
            </Card>
          ) : null}

          <section aria-labelledby="ranking-list-title">
            <div className="mb-3 flex items-center justify-between gap-4">
              <h2 id="ranking-list-title" className="text-lg font-semibold text-foreground">
                {t("ranking.top")}
              </h2>
              <span className="text-sm text-muted-foreground">
                {t("ranking.participants", { count: data.total_users })}
              </span>
            </div>

            {data.top.length === 0 ? (
              <p className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
                {t("ranking.empty")}
              </p>
            ) : (
              <ol className="overflow-hidden rounded-lg border border-border bg-card">
                {data.top.map((entry) => {
                  const isCurrentUser = entry.user_id === currentUserId
                  return (
                    <li
                      key={entry.user_id}
                      className={cn(
                        "flex items-center gap-4 border-b border-border px-4 py-4 last:border-b-0",
                        isCurrentUser && "bg-primary/10"
                      )}
                    >
                      <div
                        className="flex w-9 shrink-0 justify-center"
                        aria-label={`#${entry.position}`}
                      >
                        {entry.position <= 3 ? (
                          entry.position === 1 ? (
                            <Crown className={cn("size-5", PODIUM_STYLES[0])} aria-hidden="true" />
                          ) : (
                            <Medal
                              className={cn("size-5", PODIUM_STYLES[entry.position - 1])}
                              aria-hidden="true"
                            />
                          )
                        ) : (
                          <span className="text-sm font-semibold text-muted-foreground">
                            {entry.position}
                          </span>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium text-foreground">
                          {entry.name}
                          {isCurrentUser ? (
                            <span className="ml-2 text-xs font-normal text-primary">
                              {t("ranking.you")}
                            </span>
                          ) : null}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold tabular-nums text-foreground">{entry.score}</p>
                        <p className="text-xs text-muted-foreground">{t("ranking.points")}</p>
                      </div>
                    </li>
                  )
                })}
              </ol>
            )}
          </section>
        </>
      ) : null}
    </div>
  )
}
