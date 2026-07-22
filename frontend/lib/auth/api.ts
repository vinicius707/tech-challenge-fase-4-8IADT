import type { OperatorRole, SessionData } from "@/lib/auth/session";

type LoginSuccessBody = {
  access_token: string;
  refresh_token: string;
  operator: {
    username: string;
    role: OperatorRole;
  };
};

export type AuthSuccess = { ok: true; data: SessionData };
export type AuthFailure = { ok: false; status: number; message: string };
export type AuthResult = AuthSuccess | AuthFailure;

const GENERIC_LOGIN_ERROR = "Credenciais inválidas. Tente novamente.";

export async function login(
  username: string,
  password: string,
): Promise<AuthResult> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      message: GENERIC_LOGIN_ERROR,
    };
  }

  const body = (await response.json()) as LoginSuccessBody;
  return {
    ok: true,
    data: {
      accessToken: body.access_token,
      refreshToken: body.refresh_token,
      username: body.operator.username,
      role: body.operator.role,
    },
  };
}

export async function refreshSession(
  refreshToken: string,
): Promise<AuthResult> {
  const response = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      message: "Sessão expirada. Faça login novamente.",
    };
  }

  const body = (await response.json()) as LoginSuccessBody;
  return {
    ok: true,
    data: {
      accessToken: body.access_token,
      refreshToken: body.refresh_token,
      username: body.operator.username,
      role: body.operator.role,
    },
  };
}

export async function logout(tokens: {
  accessToken: string;
  refreshToken: string | null;
}): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${tokens.accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: tokens.refreshToken }),
  });
}
