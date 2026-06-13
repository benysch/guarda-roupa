import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

const { composeLook, packCapsule } = await import("@/lib/brain");

beforeEach(() => {
  process.env.BRAIN_URL = "https://brain.example.com";
  process.env.BRAIN_SECRET = "sekret";
  vi.unstubAllGlobals();
});

describe("composeLook", () => {
  it("chama /api/look com os params e o header de segredo", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        occasion: "festa",
        season: "inverno",
        rationale: "porque sim",
        missing: [],
        pieces: [],
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const out = await composeLook("festa", "inverno");

    const [calledUrl, calledOpts] = fetchMock.mock.calls[0] as [
      URL,
      { headers: Record<string, string> },
    ];
    const u = new URL(calledUrl.toString());
    expect(u.pathname).toBe("/api/look");
    expect(u.searchParams.get("occasion")).toBe("festa");
    expect(u.searchParams.get("season")).toBe("inverno");
    expect(calledOpts.headers["X-Brain-Secret"]).toBe("sekret");
    expect(out.rationale).toBe("porque sim");
  });

  it("lança erro quando o cérebro responde não-ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) })),
    );
    await expect(composeLook("festa")).rejects.toThrow();
  });
});

describe("packCapsule", () => {
  it("chama /api/capsule com todos os params da viagem", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        days: 3,
        occasion: "trabalho",
        night: "encontro",
        season: "inverno",
        total: 0,
        groups: [],
        looks: [],
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const out = await packCapsule("3", "trabalho", "encontro", "inverno");

    const [calledUrl] = fetchMock.mock.calls[0] as [URL];
    const u = new URL(calledUrl.toString());
    expect(u.pathname).toBe("/api/capsule");
    expect(u.searchParams.get("days")).toBe("3");
    expect(u.searchParams.get("occasion")).toBe("trabalho");
    expect(u.searchParams.get("night")).toBe("encontro");
    expect(u.searchParams.get("season")).toBe("inverno");
    expect(out.days).toBe(3);
  });
});
