// finish.ts — the one Finish, at the foot of the question list.
//
// Autosave writes a draft that nothing downstream can see, and Finish is
// the only thing that submits. That button used
// to sit under each answer, over the bottom of the field, and it had to
// be pressed once per question: on 2026-11-04 thirteen answers on one
// page stayed drafts because none of their buttons was. Now there is one,
// below the last question, and it submits every draft in scope.
//
// The rules live here rather than in the component so that Node can run
// them (`tests/qapanels/finish.test.ts`). Nothing here talks to the
// server: `submitDrafts` is handed the one write it may make, which is
// the existing per-answer submit route. There is no batch route, and one
// is not needed — each submission is the same write Finish always made.

import type { QuestionListing } from './types';

/** One draft on the page, as a submission needs it. */
export interface Draft {
  docSlug: string;
  path: string;
  label: string;
  /** The draft's text, which is what gets submitted. */
  answer: string;
  /** Whether this draft revises an answer that was already submitted. */
  revises: boolean;
}

/** What the button says and whether it can be pressed. */
export interface FinishState {
  disabled: boolean;
  label: string;
  title: string;
}

/** What one press came to. */
export interface FinishReport {
  submitted: Draft[];
  failed: { draft: Draft; reason: string }[];
}

/**
 * Every draft the listing carries, in list order. A question's `answer`
 * is its draft whenever `hasDraft` is set (`routes._question`), and the
 * store never records an empty or unchanged draft, so `hasDraft` is the
 * whole test.
 */
export function pendingDrafts(listing: QuestionListing | null): Draft[] {
  if (!listing) return [];
  const drafts: Draft[] = [];
  for (const entry of listing.documents) {
    for (const question of entry.questions) {
      if (!question.hasDraft) continue;
      drafts.push({
        docSlug: entry.docSlug,
        path: entry.path,
        label: question.label,
        answer: question.answer,
        revises: question.submitted,
      });
    }
  }
  return drafts;
}

/**
 * The button. `unsaved` is the editor holding text its autosave has not
 * written yet: a press settles that first, so it counts as a draft here,
 * and `unsavedRevises` says whether it is typed over a submitted answer.
 */
export function finishState(
  drafts: Draft[],
  unsaved: boolean,
  unsavedRevises: boolean,
  busy: boolean
): FinishState {
  const pending = drafts.length > 0 || unsaved;
  const revising = drafts.some((draft) => draft.revises) || (unsaved && unsavedRevises);
  const label = revising ? 'Submit revisions' : 'Finish';
  if (busy) return { disabled: true, label, title: 'Submitting…' };
  if (!pending) {
    return {
      disabled: true,
      label,
      title: 'Nothing to submit: every answer here is submitted or empty.',
    };
  }
  const count = drafts.length;
  return {
    disabled: false,
    label,
    title: revising
      ? 'Submit every draft below. A submitted answer a revision replaces is kept, not lost.'
      : `Submit every draft below${count ? ` (${count})` : ''}. Until then, nobody downstream sees them.`,
  };
}

/**
 * Submit each draft through `submit`, one at a time. One at a time
 * because each write rewrites the project's answer file whole, so two in
 * flight at once would race for it. A failure is recorded and the rest
 * still go: one bad answer is no reason to leave twelve good ones drafts.
 */
export async function submitDrafts(
  drafts: Draft[],
  submit: (draft: Draft) => Promise<void>,
  describe: (err: unknown) => string = (err) => String(err)
): Promise<FinishReport> {
  const report: FinishReport = { submitted: [], failed: [] };
  for (const draft of drafts) {
    try {
      await submit(draft);
      report.submitted.push(draft);
    } catch (err) {
      report.failed.push({ draft, reason: describe(err) });
    }
  }
  return report;
}

/** The report, in one line, shown beside the button. */
export function describeReport(report: FinishReport): string {
  const done = report.submitted.length;
  const total = done + report.failed.length;
  if (total === 0) return 'Nothing to submit.';
  const answers = (n: number) => `${n} answer${n === 1 ? '' : 's'}`;
  if (report.failed.length === 0) return `Submitted ${answers(done)}.`;
  const failed = report.failed
    .map(({ draft, reason }) => `${draft.label} (${draft.path}): ${reason}`)
    .join('; ');
  return `Submitted ${done} of ${answers(total)}. Not submitted — ${failed}`;
}
