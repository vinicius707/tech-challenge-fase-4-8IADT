import { describe, expect, it } from "vitest";

import {
  guestBlockedFromApp,
  loggedInBlockedFromLogin,
} from "@/lib/auth/routing";

describe("auth routing", () => {
  it("guest deve ir para /login ao acessar área autenticada", () => {
    expect(guestBlockedFromApp(false)).toBe("/login");
    expect(guestBlockedFromApp(true)).toBeNull();
  });

  it("autenticado em /login deve ir para /", () => {
    expect(loggedInBlockedFromLogin(true)).toBe("/");
    expect(loggedInBlockedFromLogin(false)).toBeNull();
  });
});
