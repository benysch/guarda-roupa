import { describe, expect, it } from "vitest";
import { CATEGORY_LABELS, CATEGORY_ORDER, COLOR_HEX, titleCase } from "@/lib/labels";

describe("titleCase", () => {
  it("formata snake_case e trata null", () => {
    expect(titleCase("animal_print")).toBe("Animal Print");
    expect(titleCase("couro_sintetico")).toBe("Couro Sintetico");
    expect(titleCase(null)).toBe("");
    expect(titleCase(undefined)).toBe("");
  });
});

describe("vocabulário de categorias", () => {
  it("toda categoria da ordem tem um rótulo", () => {
    for (const c of CATEGORY_ORDER) {
      expect(CATEGORY_LABELS[c]).toBeTruthy();
    }
  });

  it("cores promovidas têm hex", () => {
    expect(COLOR_HEX["vermelho"]).toMatch(/^#/);
    expect(COLOR_HEX["azul"]).toMatch(/^#/);
  });
});
