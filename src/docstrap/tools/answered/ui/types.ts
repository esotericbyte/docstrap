// types.ts — the shape of what `GET /api/answers/{project}/{doc}` returns.
//
// Mirrors `docstrap.server._answers_payload`, the READING projection of
// `docstrap.pairing.pair`. No draft appears in it,
// which is why this tool cannot accidentally publish one: there is
// nothing here to publish.

export interface AnsweredQuestion {
  key: string | null;
  docSlug: string;
  document: string;
  docId: string | null;
  label: string;
  question: string;
  section: string;
  line: number;
  answered: boolean;
  /** The submitted prose, or empty. Never a draft. */
  answer: string;
  answeredAt: string | null;
  answeredBy: string | null;
  submittedAt: string | null;
  /** How many earlier answers this question has had, all still kept. */
  superseded: number;
}

export interface AnswersListing {
  project: string;
  title: string;
  docSlug: string | null;
  include: string;
  count: number;
  answered: number;
  open: number;
  questions: AnsweredQuestion[];
}
