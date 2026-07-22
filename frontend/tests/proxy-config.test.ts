import { describe, expect, it } from "vitest";

import { apiRewrites } from "../proxy.mjs";

describe("proxy rewrite", () => {
  it("encaminha /api para o backend sem o prefixo", () => {
    const rules = apiRewrites("http://backend:8000");
    expect(rules).toHaveLength(1);
    expect(rules[0].source).toBe("/api/:path*");
    expect(rules[0].destination).toBe("http://backend:8000/:path*");
  });

  it("usa localhost por padrão", () => {
    const rules = apiRewrites(undefined);
    expect(rules[0].destination).toBe("http://localhost:8000/:path*");
  });
});
