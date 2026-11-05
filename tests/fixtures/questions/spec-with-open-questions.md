# changeorders — change orders as ledger entries

A spec that ends the way every spec in this corpus ends. Everything above
the last section is prose, and some of that prose asks questions that are
answered on the spot: what is a change order? It is a ledger entry.

## 7 Deliberately out of scope for v1

No daemon: the ledger is files in git.

## 8 Open questions

Q1. Should `issue` be allowed to run from a dirty working tree, or only
against committed refs? Running against the worktree is what makes the
pre-commit hook useful, but it means an order can cite a state that never
became a commit.

Q2. Does an order belong to a branch or to a repository? Injecting into
`change_orders/` puts it on a branch, which means a rebase can lose it
while the ledger copy survives.

Q3. Who is allowed to approve? Today `approve` records `$USER` with no
check. A single-operator estate makes this moot now and wrong later.

## 9 Risks

A section after the questions. The questions are still the questions.
