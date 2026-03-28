import { useUnmatched } from "../../context/UnmatchedContext";
import UnmatchedSummary from "../utils/UnmatchedSummary";

function UnmatchedStats({ onMissingClick }) {
  const { unmatchedData } = useUnmatched();
  const disableCollections = unmatchedData.disableCollections;
  const showAllUnmatched = unmatchedData.showAllUnmatched;
  const counts = unmatchedData.unmatchedCounts;

  const unmatchedMovies = showAllUnmatched
    ? counts.unmatched_movies_all
    : counts.unmatched_movies_with_file;
  const unmatchedSeries = showAllUnmatched
    ? counts.unmatched_series_all
    : counts.unmatched_series_with_file;
  const unmatchedSeasons = showAllUnmatched
    ? counts.unmatched_seasons_all
    : counts.unmatched_seasons_with_file;
  const unmatchedGrandTotal = showAllUnmatched
    ? counts.unmatched_grand_total_all
    : counts.unmatched_grand_total_with_file;
  const totalMovies = showAllUnmatched
    ? counts.total_movies_all
    : counts.total_movies_with_file;
  const totalSeries = showAllUnmatched
    ? counts.total_series_all
    : counts.total_series_with_episodes;
  const totalSeasons = showAllUnmatched
    ? counts.total_seasons_all
    : counts.total_seasons_with_episodes;
  const grandTotal = showAllUnmatched
    ? counts.grand_total_all
    : counts.grand_total_with_file;
  const percentMovies = showAllUnmatched
    ? counts.percent_complete_movies_all
    : counts.percent_complete_movies_with_file;
  const percentSeries = showAllUnmatched
    ? counts.percent_complete_series_all
    : counts.percent_complete_series_with_episodes;
  const percentSeasons = showAllUnmatched
    ? counts.percent_complete_seasons_all
    : counts.percent_complete_seasons_with_episodes;

  const effectiveMissingCount = disableCollections
    ? unmatchedGrandTotal - counts.unmatched_collections
    : unmatchedGrandTotal;

  const effectiveTotalCount = disableCollections
    ? grandTotal - counts.total_collections
    : grandTotal;

  const effectivePercent =
    effectiveTotalCount > 0
      ? `${((100 * (effectiveTotalCount - effectiveMissingCount)) / effectiveTotalCount).toFixed(2)}%`
      : "0%";

  return (
    <div className="flex w-full flex-col gap-2">
      {!disableCollections && (
        <UnmatchedSummary
          type="all"
          missingCount={effectiveMissingCount}
          totalCount={effectiveTotalCount}
          percentComplete={effectivePercent}
          onMissingClick={onMissingClick}
        />
      )}
      <div className="grid w-full gap-2 lg:grid-cols-2">
        {disableCollections && (
          <UnmatchedSummary
            type="all"
            missingCount={effectiveMissingCount}
            totalCount={effectiveTotalCount}
            percentComplete={effectivePercent}
            onMissingClick={onMissingClick}
          />
        )}
        <UnmatchedSummary
          type="movies"
          missingCount={unmatchedMovies}
          totalCount={totalMovies}
          percentComplete={percentMovies}
          onMissingClick={onMissingClick}
        />
        {!disableCollections && (
          <UnmatchedSummary
            type="collections"
            missingCount={counts.unmatched_collections}
            totalCount={counts.total_collections}
            percentComplete={counts.percent_complete_collections}
            onMissingClick={onMissingClick}
          />
        )}
        <UnmatchedSummary
          type="series (main posters)"
          missingCount={unmatchedSeries}
          totalCount={totalSeries}
          percentComplete={percentSeries}
          onMissingClick={onMissingClick}
        />
        <UnmatchedSummary
          type="seasons"
          missingCount={unmatchedSeasons}
          totalCount={totalSeasons}
          percentComplete={percentSeasons}
          onMissingClick={onMissingClick}
        />
      </div>
    </div>
  );
}
export default UnmatchedStats;
