import { beforeEach, describe, expect, it, vi } from "vitest";

// Recorder do cliente Supabase mockado (hoisted: roda antes dos imports).
const h = vi.hoisted(() => {
  const rec: Record<string, unknown> = {};
  const sb = {
    from: vi.fn(() => ({
      update: vi.fn((payload: unknown) => {
        rec.update = payload;
        return {
          eq: vi.fn((c: string, v: string) => {
            rec.updEq = [c, v];
            return { error: null };
          }),
        };
      }),
      delete: vi.fn(() => ({
        eq: vi.fn((c: string, v: string) => {
          rec.delEq = [c, v];
          return { error: null };
        }),
      })),
      select: vi.fn(() => ({
        eq: vi.fn(() => ({
          limit: vi.fn(() => ({
            maybeSingle: vi.fn(() => ({
              data: { id: "g1", category: "top" },
              error: null,
            })),
          })),
        })),
      })),
    })),
    storage: {
      from: vi.fn(() => ({
        remove: vi.fn((paths: string[]) => {
          rec.removed = paths;
          return { error: null };
        }),
      })),
    },
  };
  return { rec, sb };
});

vi.mock("server-only", () => ({}));
vi.mock("@/lib/supabase", () => ({
  supabaseAdmin: () => h.sb,
  BUCKET: "wardrobe",
}));

const { updateGarment, deleteGarment, getGarment } = await import(
  "@/lib/wardrobe"
);

beforeEach(() => {
  for (const k of Object.keys(h.rec)) delete h.rec[k];
});

describe("updateGarment", () => {
  it("envia só campos editáveis, descarta desconhecidos e converte '' em null", async () => {
    await updateGarment("g1", {
      category: "bottom",
      primary_color: "",
      brand: "Arezzo",
      naoExiste: "ignora",
    } as Record<string, string | null>);

    expect(h.rec.update).toEqual({
      category: "bottom",
      primary_color: null,
      brand: "Arezzo",
    });
    expect(h.rec.updEq).toEqual(["id", "g1"]);
  });
});

describe("deleteGarment", () => {
  it("remove o objeto do Storage e apaga a linha", async () => {
    await deleteGarment("g1");
    expect(h.rec.removed).toEqual(["g1.jpg"]);
    expect(h.rec.delEq).toEqual(["id", "g1"]);
  });
});

describe("getGarment", () => {
  it("retorna a peça encontrada", async () => {
    const g = await getGarment("g1");
    expect(g?.id).toBe("g1");
  });
});
