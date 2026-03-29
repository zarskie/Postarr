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
      total_movies_all: 0,
      total_series_all: 0,
      total_seasons_all: 0,
      percent_complete_movies_all: "0%",
      percent_complete_series_all: "0%",
      percent_complete_seasons_all: "0%",
      grand_total_all: 0,
      percent_complete_grand_total_all: "0%",
      total_movies_with_file: 0,
      total_series_with_episodes: 0,
      total_seasons_with_episodes: 0,
      percent_complete_movies_with_file: "0%",
      percent_complete_series_with_episodes: "0%",
      percent_complete_seasons_with_episodes: "0%",
      grand_total_with_file: 0,
      percent_complete_grand_total_with_file: "0%",
      total_collections: 0,
      percent_complete_collections: "0%",
      unmatched_movies_all: 0,
      unmatched_movies_with_file: 0,
      unmatched_series_all: 0,
      unmatched_series_with_file: 0,
      unmatched_seasons_all: 0,
      unmatched_seasons_with_file: 0,
      unmatched_collections: 0,
      unmatched_grand_total_all: 0,
      unmatched_grand_total_with_file: 0,
    },
    disableCollections: false,
    showAllUnmatched: false,
  });

  const refreshUnmatchedData = async () => {
    try {
      const response = await fetch("/api/poster-renamer/unmatched-assets");
      const result = await response.json();
      if (result.success) {
        const allMedia = result.unmatched_media;
        const showAllUnmatched = result.show_all_unmatched;

        const filteredMedia = showAllUnmatched
          ? allMedia
          : {
              movies: allMedia.movies.filter((m) => !m.is_missing),
              collections: allMedia.collections,
              shows: allMedia.shows
                .map((show) => ({
                  ...show,
                  seasons: show.seasons.filter((s) => !s.is_missing),
                }))
                .filter(
                  (show) =>
                    !show.is_missing &&
                    (show.main_poster_missing || show.seasons.length > 0),
                ),
            };
        setUnmatchedData({
          unmatchedMedia: filteredMedia,
          unmatchedCounts: result.unmatched_counts,
          disableCollections: result.disable_collections,
          showAllUnmatched: result.show_all_unmatched,
        });
      }
    } catch (error) {
      console.error("Error fetching unmatched assets:", error);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refreshUnmatchedData();
  }, []);
  console.log(unmatchedData);

  return (
    <UnmatchedContext.Provider value={{ unmatchedData, refreshUnmatchedData }}>
      {children}
    </UnmatchedContext.Provider>
  );
}
