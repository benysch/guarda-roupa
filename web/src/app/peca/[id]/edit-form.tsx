"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { CATEGORY_LABELS, CATEGORY_ORDER, COLOR_HEX, titleCase } from "@/lib/labels";
import { COLORS, MATERIALS, PATTERNS } from "@/lib/vocab";
import type { Garment } from "@/lib/wardrobe";
import { removeGarment, saveGarment } from "./actions";

const CATEGORIES: [string, string][] = CATEGORY_ORDER.map((c) => [
  c,
  CATEGORY_LABELS[c],
]);
const COLOR_OPTS: [string, string][] = COLORS.map((c) => [c, titleCase(c)]);

export function EditForm({ g }: { g: Garment }) {
  const router = useRouter();
  const [category, setCategory] = useState(g.category);
  const [color, setColor] = useState(g.primary_color ?? "");
  const [pattern, setPattern] = useState(g.pattern ?? "");
  const [material, setMaterial] = useState(g.material ?? "");
  const [brand, setBrand] = useState(g.brand ?? "");
  const [model, setModel] = useState(g.model_name ?? "");
  const [saving, startSave] = useTransition();
  const [deleting, startDel] = useTransition();

  function save() {
    startSave(async () => {
      try {
        await saveGarment(g.id, {
          category,
          primary_color: color,
          pattern,
          material,
          brand,
          model_name: model,
        });
        toast.success("Peça atualizada");
        router.refresh();
      } catch {
        toast.error("Não consegui salvar");
      }
    });
  }

  function del() {
    if (!confirm("Apagar esta peça? Não dá pra desfazer.")) return;
    startDel(async () => {
      try {
        await removeGarment(g.id);
      } catch {
        toast.error("Não consegui apagar");
      }
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl tracking-tight">
          {titleCase(g.subcategory ?? g.category)}
        </h1>
        {g.description && (
          <p className="mt-2 text-sm text-muted-foreground">{g.description}</p>
        )}
      </div>

      <Field label="Categoria">
        {CATEGORIES.map(([v, l]) => (
          <Chip key={v} label={l} active={category === v} onClick={() => setCategory(v)} />
        ))}
      </Field>

      <Field label="Cor">
        {COLOR_OPTS.map(([v, l]) => (
          <Chip
            key={v}
            label={l}
            active={color === v}
            onClick={() => setColor(v)}
            swatch={COLOR_HEX[v]}
          />
        ))}
      </Field>

      <Field label="Estampa">
        {PATTERNS.map(([v, l]) => (
          <Chip key={v} label={l} active={pattern === v} onClick={() => setPattern(v)} />
        ))}
      </Field>

      <Field label="Material">
        {MATERIALS.map(([v, l]) => (
          <Chip key={v} label={l} active={material === v} onClick={() => setMaterial(v)} />
        ))}
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="tracking-label mb-2 text-[10px] uppercase text-muted-foreground">
            Marca
          </p>
          <Input value={brand} onChange={(e) => setBrand(e.target.value)} />
        </div>
        <div>
          <p className="tracking-label mb-2 text-[10px] uppercase text-muted-foreground">
            Modelo
          </p>
          <Input value={model} onChange={(e) => setModel(e.target.value)} />
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="tracking-label rounded-md bg-primary px-6 py-2.5 text-[11px] uppercase text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {saving ? "Salvando…" : "Salvar"}
        </button>
        <button
          type="button"
          onClick={del}
          disabled={deleting}
          className="tracking-label rounded-md px-4 py-2.5 text-[11px] uppercase text-destructive transition-colors hover:bg-destructive/10 disabled:opacity-50"
        >
          {deleting ? "Apagando…" : "Apagar"}
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="tracking-label mb-2 text-[10px] uppercase text-muted-foreground">
        {label}
      </p>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  );
}

function Chip({
  label,
  active,
  onClick,
  swatch,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  swatch?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`tracking-label inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] uppercase transition-colors ${
        active
          ? "border-foreground bg-foreground text-background"
          : "border-border text-muted-foreground hover:border-foreground hover:text-foreground"
      }`}
    >
      {swatch && (
        <span
          className="h-2.5 w-2.5 rounded-full ring-1 ring-black/10"
          style={{ backgroundColor: swatch }}
        />
      )}
      {label}
    </button>
  );
}
