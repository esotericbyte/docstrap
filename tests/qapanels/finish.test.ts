// The panels' one Finish — `ui/finish.ts` under Node.
//
// Run by `npm test` in packages/docstrap, and by
// `tests/test_qapanels_finish.py`, which is how `pytest` reaches it.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  describeReport,
  finishState,
  pendingDrafts,
  submitDrafts,
  type Draft,
} from '../../src/docstrap/tools/qapanels/ui/finish.ts';
import type { QuestionItem, QuestionListing } from '../../src/docstrap/tools/qapanels/ui/types.ts';

function question(label: string, over: Partial<QuestionItem> = {}): QuestionItem {
  return {
    label,
    number: Number(label.slice(1)),
    text: `Question ${label}?`,
    section: 'Open questions',
    line: 1,
    key: `DOC:${label}`,
    answer: '',
    submittedAnswer: '',
    answeredAt: null,
    submitted: false,
    submittedAt: null,
    hasDraft: false,
    draftedAt: null,
    supersededCount: 0,
    ...over,
  };
}

function page(questions: QuestionItem[]): QuestionListing {
  return {
    project: 'packages__thing',
    title: 'The Thing',
    documents: [
      { docSlug: 'spec', path: 'docs/spec.md', docId: 'DOC', questions, answersDoneRoute: null },
    ],
    count: questions.length,
    open: questions.filter((q) => !q.submitted).length,
  };
}

const threeDrafts = page([
  question('Q1', { answer: 'one', hasDraft: true }),
  question('Q2', { answer: 'two', hasDraft: true }),
  question('Q3', { answer: 'three', hasDraft: true }),
  question('Q4'),
]);

test('a page with three drafts submits all three from the one Finish', async () => {
  const drafts = pendingDrafts(threeDrafts);
  const state = finishState(drafts, false, false, false);
  assert.equal(state.disabled, false);
  assert.equal(state.label, 'Finish');

  const sent: Draft[] = [];
  const report = await submitDrafts(drafts, async (draft) => {
    sent.push(draft);
  });
  assert.deepEqual(
    sent.map((d) => [d.label, d.answer]),
    [
      ['Q1', 'one'],
      ['Q2', 'two'],
      ['Q3', 'three'],
    ]
  );
  assert.equal(report.submitted.length, 3);
  assert.equal(report.failed.length, 0);
  assert.equal(describeReport(report), 'Submitted 3 answers.');
});

test('a page with no drafts has Finish disabled, with a hint saying so', () => {
  const none = page([
    question('Q1'),
    question('Q2', { answer: 'kept', submittedAnswer: 'kept', submitted: true }),
  ]);
  const drafts = pendingDrafts(none);
  assert.deepEqual(drafts, []);
  const state = finishState(drafts, false, false, false);
  assert.equal(state.disabled, true);
  assert.match(state.title, /Nothing to submit/);
});

test('typing the autosave has not written yet still counts as something to submit', () => {
  const state = finishState([], true, false, false);
  assert.equal(state.disabled, false);
});

test('a draft over a submitted answer makes the label "Submit revisions"', () => {
  const listing = page([
    question('Q1', { answer: 'new', submittedAnswer: 'old', submitted: true, hasDraft: true }),
    question('Q2', { answer: 'fresh', hasDraft: true }),
  ]);
  const drafts = pendingDrafts(listing);
  assert.deepEqual(
    drafts.map((d) => d.revises),
    [true, false]
  );
  assert.equal(finishState(drafts, false, false, false).label, 'Submit revisions');
  assert.equal(finishState([], true, true, false).label, 'Submit revisions');
});

test('a failure is reported by name and the rest are still submitted', async () => {
  const drafts = pendingDrafts(threeDrafts);
  const report = await submitDrafts(
    drafts,
    async (draft) => {
      if (draft.label === 'Q2') throw new Error('HTTP 400');
    },
    (err) => (err as Error).message
  );
  assert.deepEqual(
    report.submitted.map((d) => d.label),
    ['Q1', 'Q3']
  );
  assert.equal(
    describeReport(report),
    'Submitted 2 of 3 answers. Not submitted — Q2 (docs/spec.md): HTTP 400'
  );
});

test('submissions go one at a time, because each rewrites the answer file whole', async () => {
  let inFlight = 0;
  let most = 0;
  await submitDrafts(pendingDrafts(threeDrafts), async () => {
    inFlight += 1;
    most = Math.max(most, inFlight);
    await new Promise((resolve) => setTimeout(resolve, 5));
    inFlight -= 1;
  });
  assert.equal(most, 1);
});

test('a busy Finish cannot be pressed again', () => {
  assert.equal(finishState(pendingDrafts(threeDrafts), false, false, true).disabled, true);
});
