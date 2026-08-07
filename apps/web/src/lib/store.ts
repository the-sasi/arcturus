import { create } from "zustand";

// Workspace context — the state the AI copilot will read to know what the
// user is looking at (current module, selected instrument, …).
type WorkspaceState = {
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  selectedSymbol: "NSE:RELIANCE",
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
}));
