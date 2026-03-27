import { useUnmatched } from "../../context/UnmatchedContext";
import UnmatchedSummary from "../utils/UnmatchedSummary";

function UnmatchedStats({ onMissingClick }) {
  const { unmatchedData } = useUnmatched();
  const disableCollections = unmatchedData.disableCollections;
  const effectiveMissingCount = unmatchedData.disableCollections
    ? unmatchedData.unmatchedCounts.unmatched_grand_total -
      unmatchedData.unmatchedCounts.unmatched_collections
    : unmatchedData.unmatchedCounts.unmatched_grand_total;
  const effectiveTotalCount = unmatchedData.disableCollections
    ? unmatchedData.unmatchedCounts.grand_total -
      unmatchedData.unmatchedCounts.total_collections
    : unmatchedData.unmatchedCounts.grand_total;
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
          missingCount={unmatchedData.unmatchedCounts.unmatched_movies}
          totalCount={unmatchedData.unmatchedCounts.total_movies}
          percentComplete={
            unmatchedData.unmatchedCounts.percent_complete_movies
          }
          onMissingClick={onMissingClick}
        />
        {!disableCollections && (
          <UnmatchedSummary
            type="collections"
            missingCount={unmatchedData.unmatchedCounts.unmatched_collections}
            totalCount={unmatchedData.unmatchedCounts.total_collections}
            percentComplete={
              unmatchedData.unmatchedCounts.percent_complete_collections
            }
            onMissingClick={onMissingClick}
          />
        )}
        <UnmatchedSummary
          type="series (main posters)"
          missingCount={unmatchedData.unmatchedCounts.unmatched_series}
          totalCount={unmatchedData.unmatchedCounts.total_series}
          percentComplete={
            unmatchedData.unmatchedCounts.percent_complete_series
          }
          onMissingClick={onMissingClick}
        />
        <UnmatchedSummary
          type="seasons"
          missingCount={unmatchedData.unmatchedCounts.unmatched_seasons}
          totalCount={unmatchedData.unmatchedCounts.total_seasons}
          percentComplete={
            unmatchedData.unmatchedCounts.percent_complete_seasons
          }
          onMissingClick={onMissingClick}
        />
      </div>
    </div>
  );
}
export default UnmatchedStats;
