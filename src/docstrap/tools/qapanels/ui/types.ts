// types.ts — the shape of what `GET {prefix}/questions` returns.
//
// Mirrors `docstrap.tools.qapanels.routes.list_questions`. Nothing here
// is stored: the listing is a scan, performed per request, derived and
// disposable.

export interface QuestionItem {
  label: string;
  number: number;
  text: string;
  section: string;
  line: number;
  /** `<doc-id>:<label>`, or null until the document has an id. */
  key: string | null;
  /** What to put in the editor: the unsubmitted revision if there is
   *  one, the submitted answer otherwise. */
  answer: string;
  /** The decision. It stays put while a revision is typed over it. */
  submittedAnswer: string;
  answeredAt: string | null;
  /** Whether a person pressed Finish. Only then does the answer count. */
  submitted: boolean;
  submittedAt: string | null;
  /** Whether an unsubmitted revision is in flight against this answer. */
  hasDraft: boolean;
  draftedAt: string | null;
  /** How many earlier answers this question has had, all still kept. */
  supersededCount: number;
}

export interface QuestionDocument {
  docSlug: string;
  path: string;
  docId: string | null;
  questions: QuestionItem[];
  /** Where this document's "answers done" prompt posts, or null when no
   *  command is configured — and then there is no prompt. */
  answersDoneRoute: string | null;
}

export interface QuestionListing {
  project: string;
  title: string;
  documents: QuestionDocument[];
  /** Every question found. */
  count: number;
  /** Those nobody has finished answering. A draft is still open. */
  open: number;
}

/** One question plus the document it came from — what a row selects. */
export interface Selection {
  docSlug: string;
  path: string;
  label: string;
  text: string;
  section: string;
  key: string | null;
  answer: string;
  submittedAnswer: string;
  answeredAt: string | null;
  submitted: boolean;
  submittedAt: string | null;
  hasDraft: boolean;
  draftedAt: string | null;
  supersededCount: number;
}

/** What a submission delivered. Null for a draft. */
export interface Delivery {
  path: string;
  version: string;
  document: string;
  docSlug: string;
  docId: string | null;
  answered: number;
  open: number;
  generatedAt: string;
}

/** What the POST returns. Only `addendum` is read by the panel. */
export interface SubmitResult {
  key: string;
  addendum: Delivery | null;
}

/** What pressing "answers done" came to. */
export interface AnswersDoneResult {
  ok: boolean;
  exitStatus: number | null;
  error: string;
}

/** The last "answers done" press, shown briefly beside its prompt. */
export interface AnswersDoneNotice {
  docSlug: string;
  ok: boolean;
  text: string;
}

export function selectionId(docSlug: string, label: string): string {
  // A separator that cannot occur in a doc slug or a question label,
  // written as an escape rather than as a raw byte: a literal NUL in
  // the source makes git treat this file as binary and refuse to diff it.
  return `${docSlug}\u0000${label}`;
}
