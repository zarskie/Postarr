import { createContext, useContext } from "react";

export const UnmatchedContext = createContext(null);

export function useUnmatched() {
  return useContext(UnmatchedContext);
}
