import type { OperatorRole } from "@/lib/auth/session";

export type NavItem = {
  href: string;
  label: string;
  /** false = placeholder desabilitado (fora desta etapa). */
  enabled: boolean;
  /** Se definido, só esses papéis veem o item ativo. */
  roles?: OperatorRole[];
};

/** Navegação do shell autenticado (ADR 0026). */
export const primaryNavItems: NavItem[] = [
  { href: "/", label: "Início", enabled: true },
  { href: "/pacientes", label: "Pacientes", enabled: true },
  { href: "/alertas", label: "Alertas", enabled: true },
  {
    href: "/admin/falhas",
    label: "Falhas",
    enabled: true,
    roles: ["admin"],
  },
];

export function isNavItemVisible(
  item: NavItem,
  role: OperatorRole | null,
): boolean {
  if (!item.enabled) return false;
  if (!item.roles || item.roles.length === 0) return true;
  return role !== null && item.roles.includes(role);
}
