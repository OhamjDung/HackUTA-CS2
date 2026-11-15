/** Find a result recorded after practice began, ignoring other puzzles. */
export function newPuzzleAttempt<T extends { id: number; puzzle_id: string }>(rows: T[], puzzleId: string, after: number): T | undefined {
  return rows.find((row) => row.puzzle_id === puzzleId && row.id > after);
}
