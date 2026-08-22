"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/commands", label: "Commands" },
  { href: "/products", label: "Products" },
  { href: "/customers", label: "Customers" },
  { href: "/transactions", label: "Transactions" },
  { href: "/documents", label: "Documents" },
  { href: "/insights", label: "Insights" },
  { href: "/reminders", label: "Reminders" },
  { href: "/audit-logs", label: "Audit log" },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const { token, businessId, user, logout } = useAuthStore();

  if (!token || !businessId) return null;

  return (
    <header className="border-b border-line bg-panel">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-6 min-w-0">
          <span className="font-semibold text-sm tracking-tight shrink-0">VyaparFlow</span>
          <nav className="flex gap-4 overflow-x-auto no-scrollbar">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`text-sm px-1 pb-0.5 border-b-2 whitespace-nowrap transition-colors ${
                  pathname === l.href
                    ? "border-accent text-ink font-medium"
                    : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm text-muted shrink-0">
          <span>{user?.name}</span>
          <button
            className="text-xs underline hover:text-ink"
            onClick={() => {
              logout();
              router.push("/login");
            }}
          >
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
