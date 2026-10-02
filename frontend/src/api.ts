import type { AnalyzeResponse, Block, Options } from "./types";

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* not JSON */
  }
  return `Something went wrong (error ${res.status}). Please try again.`;
}

export async function analyze(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/analyze", { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function render(file: File, blocks: Block[], options: Options): Promise<Blob> {
  const form = new FormData();
  form.append("file", file);
  form.append("labels", JSON.stringify(blocks.map((b) => ({ index: b.index, label: b.label }))));
  form.append(
    "options",
    JSON.stringify({ ...options, running_head: options.running_head.trim() || null }),
  );
  const res = await fetch("/api/render", { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.blob();
}
