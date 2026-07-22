import { login, logout, refreshSession } from "@/lib/auth/api";
import { useSessionStore } from "@/lib/auth/session";

/**
 * fetch autenticado com renovação transparente de access via refresh (1 retry).
 */
export async function apiFetch(
  input: string,
  init: RequestInit = {},
): Promise<Response> {
  const run = async (accessToken: string | null) => {
    const headers = new Headers(init.headers);
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
    return fetch(input, { ...init, headers });
  };

  const { accessToken, refreshToken, setSession, clearSession } =
    useSessionStore.getState();

  let response = await run(accessToken);
  if (response.status !== 401 || !refreshToken) {
    return response;
  }

  const refreshed = await refreshSession(refreshToken);
  if (!refreshed.ok) {
    clearSession();
    return response;
  }

  setSession(refreshed.data);
  response = await run(refreshed.data.accessToken);
  return response;
}

export { login, logout, refreshSession };
