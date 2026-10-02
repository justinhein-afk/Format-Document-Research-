import { useState } from "react";
import { analyze, render } from "./api";
import Upload from "./components/Upload";
import Review from "./components/Review";
import OptionsPanel from "./components/OptionsPanel";
import type { AnalyzeResponse, Block, Label, Options } from "./types";

const DEFAULT_OPTIONS: Options = {
  paper_type: "student",
  font: "Times New Roman 12",
  include_title_page: true,
  running_head: "",
  title_case_headings: true,
  sort_references: true,
};

type Stage = "upload" | "analyzing" | "review";

export default function App() {
  const [stage, setStage] = useState<Stage>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [options, setOptions] = useState<Options>(DEFAULT_OPTIONS);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  async function handleFile(f: File) {
    setError(null);
    setFile(f);
    setStage("analyzing");
    try {
      const res = await analyze(f);
      setResult(res);
      setBlocks(res.blocks);
      setStage("review");
    } catch (e) {
      setError((e as Error).message);
      setStage("upload");
    }
  }

  function relabel(index: number, label: Label) {
    setBlocks((prev) =>
      prev.map((b) => (b.index === index ? { ...b, label, confidence: 1, source: "user" } : b)),
    );
  }

  async function download() {
    if (!file) return;
    setError(null);
    setDownloading(true);
    try {
      const blob = await render(file, blocks, options);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${file.name.replace(/\.docx$/i, "")} (APA).docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDownloading(false);
    }
  }

  function reset() {
    setStage("upload");
    setFile(null);
    setResult(null);
    setBlocks([]);
    setError(null);
  }

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={reset} aria-label="Start over">
          <span className="logo">A</span>
          <span>APA Formatter</span>
        </button>
        <span className="tag">APA 7th edition · free</span>
      </header>

      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}

      {stage !== "review" && (
        <main className="landing">
          <h1>Format your research paper in APA 7</h1>
          <p className="lede">
            Upload an unformatted Word document. We detect the title page, abstract, headings, figures,
            tables and references, let you check them, and give you back a properly formatted .docx.
          </p>
          <Upload onFile={handleFile} busy={stage === "analyzing"} fileName={file?.name} />
          <ul className="facts">
            <li>Times New Roman 12, double spacing, 1&Prime; margins, page numbers</li>
            <li>Title page, abstract, five heading levels, hanging-indent references</li>
            <li>Images, tables, equations and links are kept</li>
          </ul>
          <p className="privacy">
            Your file is processed in memory and deleted right away. It is never stored or used for training.
          </p>
        </main>
      )}

      {stage === "review" && result && (
        <main className="workspace">
          <section className="review-pane">
            <div className="pane-head">
              <div>
                <h2>Check the structure</h2>
                <p className="muted">
                  {file?.name} · {blocks.length} blocks
                  {result.ai_used ? " · labeled with AI" : ""}
                </p>
              </div>
            </div>
            {result.warnings.map((w) => (
              <div key={w} className="alert warn">
                {w}
              </div>
            ))}
            <Review blocks={blocks} onRelabel={relabel} />
          </section>
          <aside className="side-pane">
            <OptionsPanel options={options} onChange={setOptions} />
            <button className="primary" onClick={download} disabled={downloading}>
              {downloading ? "Formatting…" : "Download APA .docx"}
            </button>
            <button className="ghost" onClick={reset}>
              Format another paper
            </button>
            <p className="muted small">
              Always proofread the result. Citation content is not rewritten, only laid out.
            </p>
          </aside>
        </main>
      )}
    </div>
  );
}
