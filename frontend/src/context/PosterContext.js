import { createContext, useContext } from "react";

export const PosterContext = createContext(null);

export function usePoster() {
  return useContext(PosterContext);
}
