export type NavItem = {
  href: string;
  label: string;
  /** false = placeholder desabilitado (fora desta etapa). */
  enabled: boolean;
};

/** Navegação mínima do shell autenticado (ADR 0026, subconjunto Épico 4). */
export const primaryNavItems: NavItem[] = [
  { href: "/", label: "Início", enabled: true },
  { href: "/pacientes", label: "Pacientes", enabled: true },
  { href: "/alertas", label: "Alertas", enabled: false },
  { href: "/admin/falhas", label: "Admin", enabled: false },
];
