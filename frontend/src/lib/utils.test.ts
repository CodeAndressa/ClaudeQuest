import { describe, expect, it } from "vitest"

import { cn } from "@/lib/utils"

describe("cn", () => {
  it("combina classes e resolve conflitos do Tailwind mantendo a última", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4")
  })

  it("ignora valores falsy", () => {
    expect(cn("base", false, undefined, null, "extra")).toBe("base extra")
  })
})
