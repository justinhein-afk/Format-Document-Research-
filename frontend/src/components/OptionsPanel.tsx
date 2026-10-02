import type { Options } from "../types";

interface Props {
  options: Options;
  onChange: (o: Options) => void;
}

const FONTS = ["Times New Roman 12", "Calibri 11", "Arial 11", "Georgia 11", "Lucida Sans Unicode 10"];

export default function OptionsPanel({ options, onChange }: Props) {
  const set = <K extends keyof Options>(key: K, value: Options[K]) => onChange({ ...options, [key]: value });

  return (
    <div className="options">
      <h3>Options</h3>
      <fieldset className="segmented">
        <legend>Paper type</legend>
        {(["student", "professional"] as const).map((t) => (
          <label key={t} className={options.paper_type === t ? "on" : ""}>
            <input
              type="radio"
              name="paper_type"
              checked={options.paper_type === t}
              onChange={() => set("paper_type", t)}
            />
            {t === "student" ? "Student" : "Professional"}
          </label>
        ))}
      </fieldset>
      <p className="muted small">
        {options.paper_type === "student"
          ? "Title page lists course, instructor and date. Page numbers only in the header."
          : "Adds a running head and an author note on the title page."}
      </p>

      <label className="field">
        <span>Font</span>
        <select value={options.font} onChange={(e) => set("font", e.target.value)}>
          {FONTS.map((f) => (
            <option key={f}>{f}</option>
          ))}
        </select>
      </label>

      {options.paper_type === "professional" && (
        <label className="field">
          <span>Running head (optional)</span>
          <input
            type="text"
            maxLength={50}
            placeholder="Shortened title, up to 50 characters"
            value={options.running_head}
            onChange={(e) => set("running_head", e.target.value)}
          />
        </label>
      )}

      <label className="check">
        <input
          type="checkbox"
          checked={options.include_title_page}
          onChange={(e) => set("include_title_page", e.target.checked)}
        />
        Create a title page
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={options.title_case_headings}
          onChange={(e) => set("title_case_headings", e.target.checked)}
        />
        Title Case for title and headings
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={options.sort_references}
          onChange={(e) => set("sort_references", e.target.checked)}
        />
        Sort references alphabetically
      </label>
    </div>
  );
}
