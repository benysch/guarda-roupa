import { describe, expect, it } from "vitest";
import { COLORS, MATERIALS, PATTERNS } from "@/lib/vocab";

describe("vocabulário de edição", () => {
  it("listas não vazias", () => {
    expect(COLORS.length).toBeGreaterThan(0);
    expect(PATTERNS.length).toBeGreaterThan(0);
    expect(MATERIALS.length).toBeGreaterThan(0);
  });

  it("sem valores duplicados", () => {
    expect(new Set(COLORS).size).toBe(COLORS.length);
    const pv = PATTERNS.map(([v]) => v);
    expect(new Set(pv).size).toBe(pv.length);
    const mv = MATERIALS.map(([v]) => v);
    expect(new Set(mv).size).toBe(mv.length);
  });
});
