/** Regras puras de redirecionamento (guard de rotas). */

export function guestBlockedFromApp(isAuthenticated: boolean): string | null {
  return isAuthenticated ? null : "/login";
}

export function loggedInBlockedFromLogin(
  isAuthenticated: boolean,
): string | null {
  return isAuthenticated ? "/" : null;
}
