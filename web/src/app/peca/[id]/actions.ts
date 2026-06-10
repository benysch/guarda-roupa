"use server";

import { redirect } from "next/navigation";
import { isAuthed } from "@/lib/auth";
import { deleteGarment, updateGarment } from "@/lib/wardrobe";

export async function saveGarment(
  id: string,
  fields: Record<string, string | null>,
): Promise<void> {
  if (!(await isAuthed())) throw new Error("não autorizado");
  await updateGarment(id, fields);
}

export async function removeGarment(id: string): Promise<void> {
  if (!(await isAuthed())) throw new Error("não autorizado");
  await deleteGarment(id);
  redirect("/");
}
