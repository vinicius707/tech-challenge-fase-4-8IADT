import { test } from "node:test";
import assert from "node:assert/strict";

import { apiRewrites } from "../proxy.mjs";

test("proxy rewrite encaminha /api para o backend sem o prefixo", () => {
  const rules = apiRewrites("http://backend:8000");
  assert.equal(rules.length, 1);
  assert.equal(rules[0].source, "/api/:path*");
  assert.equal(rules[0].destination, "http://backend:8000/:path*");
});

test("proxy rewrite usa localhost por padrão", () => {
  const rules = apiRewrites(undefined);
  assert.equal(rules[0].destination, "http://localhost:8000/:path*");
});
