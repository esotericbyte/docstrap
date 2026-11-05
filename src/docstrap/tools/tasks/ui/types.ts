// What the task tool's route sends and receives (`routes.py`).

/** One decision recorded on one task (`decisions.Decision.to_json`). */
export interface Decision {
  /** Null when the stored answer opens with no action line. */
  action: string | null;
  note: string;
  decidedAt: string;
}

/** GET: every decision recorded from this page. */
export interface PageDecisions {
  decisions: Record<string, Decision>;
  actions: string[];
  /** Where this page's "answers done" prompt posts, or null: not offered. */
  answersDoneRoute: string | null;
}

/** POST: the decision as stored. */
export interface DecisionStored {
  taskId: string;
  key: string;
  decision: Decision;
}

/** What the "answers done" route answers (`answers_done.Outcome.to_json`). */
export interface AnswersDoneResult {
  ok: boolean;
  exitStatus: number | null;
  error: string;
}
