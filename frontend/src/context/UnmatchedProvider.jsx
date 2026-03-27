import { useEffect, useState } from "react";
import { UnmatchedContext } from "./UnmatchedContext";

export function UnmatchedProvider({ children }) {
  const [unmatchedData, setUnmatchedData] = useState({
    unmatchedMedia: {
      movies: [],
      shows: [],
      collections: [],
    },
    unmatchedCounts: {
      total_movies: 0,
      percent_complete_movies: "0%",
      total_series: 0,
      percent_complete_series: "0%",
      total_seasons: 0,
      percent_complete_seasons: "0%",
      total_collections: 0,
      percent_complete_collections: "0%",
      grand_total: 0,
      percent_complete_grand_total: "0%",
      unmatched_movies: 0,
      unmatched_series: 0,
      unmatched_seasons: 0,
      unmatched_collections: 0,
      unmatched_grand_total: 0,
    },
    disableCollections: false,
  });

  const refreshUnmatchedData = async () => {
    try {
      const response = await fetch("/api/poster-renamer/unmatched-assets");
      const result = await response.json();
      if (result.success) {
        const newUnmatched = {
          unmatchedMedia: result.unmatched_media,
          unmatchedCounts: result.unmatched_counts,
          disableCollections: result.disable_collections,
        };
        setUnmatchedData(newUnmatched);
        console.log(newUnmatched);
      }
    } catch (error) {
      console.error("Error fetching unmatched assets:", error);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refreshUnmatchedData();
  }, []);

  return (
    <UnmatchedContext.Provider value={{ unmatchedData, refreshUnmatchedData }}>
      {children}
    </UnmatchedContext.Provider>
  );
}
