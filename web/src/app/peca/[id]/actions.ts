"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import {
  classifyGarment,
  deleteGarment,
  setCutoutStatus,
  updateGarment,
} from "@/lib/wardrobe";

export async function saveGarment(
  id: string,
  fields: Record<string, string | null>,
): Promise<void> {
  await updateGarment(id, fields);
}

/** Classifica uma peça crua (preenche + promove a 'processed') e volta pra fila. */
export async function classifyAndSave(
  id: string,
  fields: Record<string, string | null>,
): Promise<void> {
  await classifyGarment(id, fields);
  revalidatePath("/classificar");
  revalidatePath("/");
}

export async function removeGarment(id: string): Promise<void> {
  await deleteGarment(id);
  redirect("/");
}

export async function decideCutout(
  id: string,
  decision: "approved" | "rejected",
): Promise<void> {
  await setCutoutStatus(id, decision);
  revalidatePath(`/peca/${id}`);
  revalidatePath("/");
}
