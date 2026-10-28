import { createContext, useContext } from "react";
import type { Career, Filters } from "./api";

export type Scope = {
  career: Career;
  filters: Filters;
  selected: number | null;
  selectPlayer: (id: number | null) => void;
};
export const ScopeContext = createContext<Scope | null>(null);
export const useScope = () => {
  const value = useContext(ScopeContext);
  if (!value) throw new Error("Career scope missing");
  return value;
};
