export type Label =
  | "title" | "author" | "affiliation" | "course" | "instructor" | "date" | "author_note"
  | "abstract_heading" | "abstract_body" | "keywords"
  | "heading_1" | "heading_2" | "heading_3" | "heading_4" | "heading_5"
  | "body" | "block_quote" | "list_item" | "equation"
  | "figure" | "figure_caption" | "table" | "table_caption" | "note"
  | "reference_heading" | "reference_entry" | "appendix_heading" | "footnote_text"
  | "ignore";

export interface Block {
  index: number;
  kind: "paragraph" | "table";
  text: string;
  bold: boolean;
  italic: boolean;
  has_image: boolean;
  has_equation: boolean;
  label: Label;
  confidence: number;
  source: "rules" | "heuristic" | "ai" | "user" | "repair";
}

export interface AnalyzeResponse {
  blocks: Block[];
  ai_used: boolean;
  warnings: string[];
}

export interface Options {
  paper_type: "student" | "professional";
  font: string;
  include_title_page: boolean;
  running_head: string;
  title_case_headings: boolean;
  sort_references: boolean;
}

export type Group = "titlepage" | "abstract" | "heading" | "text" | "figure" | "refs" | "drop";

export const LABELS: { value: Label; name: string; group: Group }[] = [
  { value: "title", name: "Title", group: "titlepage" },
  { value: "author", name: "Author", group: "titlepage" },
  { value: "affiliation", name: "Affiliation", group: "titlepage" },
  { value: "course", name: "Course", group: "titlepage" },
  { value: "instructor", name: "Instructor", group: "titlepage" },
  { value: "date", name: "Date", group: "titlepage" },
  { value: "author_note", name: "Author note", group: "titlepage" },
  { value: "abstract_heading", name: "Abstract heading", group: "abstract" },
  { value: "abstract_body", name: "Abstract text", group: "abstract" },
  { value: "keywords", name: "Keywords", group: "abstract" },
  { value: "heading_1", name: "Heading 1", group: "heading" },
  { value: "heading_2", name: "Heading 2", group: "heading" },
  { value: "heading_3", name: "Heading 3", group: "heading" },
  { value: "heading_4", name: "Heading 4", group: "heading" },
  { value: "heading_5", name: "Heading 5", group: "heading" },
  { value: "body", name: "Body text", group: "text" },
  { value: "block_quote", name: "Block quote", group: "text" },
  { value: "list_item", name: "List item", group: "text" },
  { value: "equation", name: "Equation", group: "text" },
  { value: "footnote_text", name: "Footnote", group: "text" },
  { value: "figure", name: "Figure", group: "figure" },
  { value: "figure_caption", name: "Figure caption", group: "figure" },
  { value: "table", name: "Table", group: "figure" },
  { value: "table_caption", name: "Table caption", group: "figure" },
  { value: "note", name: "Note", group: "figure" },
  { value: "reference_heading", name: "References heading", group: "refs" },
  { value: "reference_entry", name: "Reference", group: "refs" },
  { value: "appendix_heading", name: "Appendix heading", group: "refs" },
  { value: "ignore", name: "Remove", group: "drop" },
];

export const LABEL_INFO = Object.fromEntries(LABELS.map((l) => [l.value, l])) as Record<
  Label,
  (typeof LABELS)[number]
>;

export const GROUP_NAMES: Record<Group, string> = {
  titlepage: "Title page",
  abstract: "Abstract",
  heading: "Headings",
  text: "Text",
  figure: "Figures & tables",
  refs: "References & appendix",
  drop: "Other",
};
