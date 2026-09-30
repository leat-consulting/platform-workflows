import { test } from "node:test";
import assert from "node:assert/strict";
import { sum } from "../src/sum.js";

test("adds numbers", () => {
  assert.equal(sum([1, 2, 3]), 6);
});

test("returns zero for an empty list", () => {
  assert.equal(sum([]), 0);
});
