import { useEffect, useState } from "react";
import { PosterContext } from "./PosterContext";

export function PosterProvider({ children }) {
  const [filePaths, setFilePaths] = useState({
    movies: [],
    collections: [],
    shows: {},
  });
  const [previewBust, setPreviewBust] = useState(() => Date.now());
  const bustPreview = () => setPreviewBust(Date.now());

  const refreshFilePaths = async () => {
    try {
      const response = await fetch("/api/poster-renamer/get-file-paths");
      const result = await response.json();
      if (result.success && result.data) {
        console.log(result.data);
        setFilePaths(result.data);
      }
    } catch (error) {
      console.error("Error fetching file paths:", error);
    }
  };
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refreshFilePaths();
  }, []);

  return (
    <PosterContext.Provider
      value={{ filePaths, refreshFilePaths, previewBust, bustPreview }}
    >
      {children}
    </PosterContext.Provider>
  );
}
