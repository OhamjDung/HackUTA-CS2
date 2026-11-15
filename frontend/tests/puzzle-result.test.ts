import assert from "node:assert/strict";
import test from "node:test";
import { newPuzzleAttempt } from "../lib/puzzle-result.ts";

test("only a newer attempt for the selected puzzle is reported", () => {
  const rows = [{ id: 8, puzzle_id: "other" }, { id: 7, puzzle_id: "seed" }];
  assert.equal(newPuzzleAttempt(rows, "seed", 6)?.id, 7);
  assert.equal(newPuzzleAttempt(rows, "seed", 7), undefined);
  assert.equal(newPuzzleAttempt(rows, "missing", 0), undefined);
});
