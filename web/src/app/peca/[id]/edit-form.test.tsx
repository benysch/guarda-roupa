// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

// dependências externas do componente, mockadas
const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, refresh }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const saveGarment = vi.fn(async () => {});
const removeGarment = vi.fn(async () => {});
vi.mock("./actions", () => ({
  saveGarment: (...a: unknown[]) => saveGarment(...a),
  removeGarment: (...a: unknown[]) => removeGarment(...a),
}));

import { EditForm } from "./edit-form";

const garment = {
  id: "g1",
  category: "top",
  subcategory: "tshirt",
  primary_color: "preto",
  material: null,
  pattern: "liso",
  formality: "casual",
  brand: null,
  model_name: null,
  description: "peça de teste",
  seasons: [],
  occasions: [],
  image_path: "g1.jpg",
  created_at: "",
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any;

beforeEach(() => {
  saveGarment.mockClear();
  removeGarment.mockClear();
  push.mockClear();
});

afterEach(() => cleanup());

describe("EditForm — render + binding (Salvar/Apagar)", () => {
  it("ao trocar a categoria e clicar Salvar, chama saveGarment com os campos certos", async () => {
    render(<EditForm g={garment} />);
    // clica no chip de categoria "Bolsas" (bag)
    fireEvent.click(screen.getByRole("button", { name: "Bolsas" }));
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(saveGarment).toHaveBeenCalledTimes(1));
    const [id, fields] = saveGarment.mock.calls[0] as [
      string,
      Record<string, string | null>,
    ];
    expect(id).toBe("g1");
    expect(fields.category).toBe("bag");
    expect(fields.primary_color).toBe("preto");
  });

  it("Apagar chama removeGarment quando o usuário confirma", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<EditForm g={garment} />);
    fireEvent.click(screen.getByRole("button", { name: "Apagar" }));
    await waitFor(() => expect(removeGarment).toHaveBeenCalledWith("g1"));
  });

  it("Apagar NÃO remove se o usuário cancela o confirm", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<EditForm g={garment} />);
    fireEvent.click(screen.getByRole("button", { name: "Apagar" }));
    expect(removeGarment).not.toHaveBeenCalled();
  });
});
