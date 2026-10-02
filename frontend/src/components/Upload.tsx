import { useRef, useState } from "react";

interface Props {
  onFile: (file: File) => void;
  busy: boolean;
  fileName?: string;
}

const MAX_BYTES = 10 * 1024 * 1024;

export default function Upload({ onFile, busy, fileName }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  function pick(files: FileList | null) {
    const f = files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".docx")) {
      setProblem("Please choose a .docx file. Old .doc files must be saved as .docx in Word first.");
      return;
    }
    if (f.size > MAX_BYTES) {
      setProblem("That file is larger than 10 MB.");
      return;
    }
    setProblem(null);
    onFile(f);
  }

  return (
    <div
      className={`dropzone${over ? " over" : ""}${busy ? " busy" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (!busy) pick(e.dataTransfer.files);
      }}
      onClick={() => !busy && input.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !busy && input.current?.click()}
    >
      <input
        ref={input}
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        hidden
        onChange={(e) => {
          pick(e.target.files);
          e.target.value = "";
        }}
      />
      {busy ? (
        <>
          <div className="spinner" aria-hidden />
          <strong>Reading {fileName}…</strong>
          <span className="muted">Detecting headings, references and more</span>
        </>
      ) : (
        <>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="1.5" />
            <path d="M14 3v5h5M12 18v-6m-3 3 3-3 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <strong>Drop your .docx here or click to choose</strong>
          <span className="muted">Up to 10 MB</span>
        </>
      )}
      {problem && <span className="problem">{problem}</span>}
    </div>
  );
}
