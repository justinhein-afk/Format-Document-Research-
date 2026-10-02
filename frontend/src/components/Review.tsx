import { useMemo, useState } from "react";
import { GROUP_NAMES, LABELS, LABEL_INFO, type Block, type Group, type Label } from "../types";

interface Props {
  blocks: Block[];
  onRelabel: (index: number, label: Label) => void;
}

const GROUP_ORDER: Group[] = ["titlepage", "abstract", "heading", "text", "figure", "refs", "drop"];

function preview(b: Block): string {
  if (b.kind === "table") return b.text || "(table)";
  if (b.has_image && !b.text) return "(image)";
  if (b.has_equation && !b.text) return "(equation)";
  return b.text || "(empty line)";
}

export default function Review({ blocks, onRelabel }: Props) {
  const [onlyUnsure, setOnlyUnsure] = useState(false);
  const [hideEmpty, setHideEmpty] = useState(true);

  const unsure = useMemo(() => blocks.filter((b) => b.confidence < 0.6).length, [blocks]);
  const visible = blocks.filter((b) => {
    if (onlyUnsure && b.confidence >= 0.6) return false;
    if (hideEmpty && b.label === "ignore" && !b.text && b.kind === "paragraph" && !b.has_image) return false;
    return true;
  });

  return (
    <div className="review">
      <div className="filters">
        <label>
          <input type="checkbox" checked={onlyUnsure} onChange={(e) => setOnlyUnsure(e.target.checked)} />
          Only show uncertain ({unsure})
        </label>
        <label>
          <input type="checkbox" checked={hideEmpty} onChange={(e) => setHideEmpty(e.target.checked)} />
          Hide blank lines
        </label>
      </div>
      {visible.length === 0 && <p className="muted">Nothing to check here. Looks good!</p>}
      <ol className="blocks">
        {visible.map((b) => {
          const info = LABEL_INFO[b.label];
          return (
            <li
              key={b.index}
              className={`block g-${info.group}${b.confidence < 0.6 ? " unsure" : ""}${
                b.label === "ignore" ? " dropped" : ""
              }`}
            >
              <select
                value={b.label}
                aria-label={`Label for block ${b.index + 1}`}
                onChange={(e) => onRelabel(b.index, e.target.value as Label)}
              >
                {GROUP_ORDER.map((g) => (
                  <optgroup key={g} label={GROUP_NAMES[g]}>
                    {LABELS.filter((l) => l.group === g).map((l) => (
                      <option key={l.value} value={l.value}>
                        {l.name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <div className={`text${b.bold ? " bold" : ""}${b.italic ? " italic" : ""}${b.kind === "table" ? " table" : ""}`}>
                {preview(b)}
              </div>
              {b.confidence < 0.6 && <span className="badge">check</span>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
