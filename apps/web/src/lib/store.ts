"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { BusinessMembershipSummary, User } from "./types";

interface AuthState {
  token: string | null;
  user: User | null;
  businessId: string | null;
  role: string | null;
  businesses: BusinessMembershipSummary[];
  needsOnboarding: boolean;
  setSession: (params: {
    token: string;
    user: User;
    businessId: string | null;
    businesses: BusinessMembershipSummary[];
    needsOnboarding: boolean;
  }) => void;
  setBusinessScope: (token: string, businessId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      businessId: null,
      role: null,
      businesses: [],
      needsOnboarding: false,
      setSession: ({ token, user, businessId, businesses, needsOnboarding }) =>
        set({ token, user, businessId, businesses, needsOnboarding }),
      setBusinessScope: (token, businessId) => set({ token, businessId }),
      logout: () =>
        set({
          token: null,
          user: null,
          businessId: null,
          role: null,
          businesses: [],
          needsOnboarding: false,
        }),
    }),
    { name: "vyaparflow-auth" }
  )
);
