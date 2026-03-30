import { Image, ImageOff, BarChart2 } from "lucide-react";
import { useState } from "react";
import PosterViewer from "../components/dashboard/PosterViewer";
import UnmatchedStats from "../components/dashboard/UnmatchedStats";
import UnmatchedAssets from "../components/dashboard/UnmatchedAssets";
import { usePoster } from "../context/PosterContext";
import { useUnmatched } from "../context/UnmatchedContext";

function Home() {
  const [activeSection, setActiveSection] = useState("poster-viewer");
  const { filePaths } = usePoster();
  const { unmatchedData } = useUnmatched();
  const sections = [
    { id: "poster-viewer", label: "Poster Viewer", icon: Image },
    { id: "unmatched-stats", label: "Unmatched Stats", icon: BarChart2 },
    { id: "unmatched-assets", label: "Unmatched Assets", icon: ImageOff },
  ];
  const [unmatchedFilter, setUnmatchedFilter] = useState("all");

  const isComplete = unmatchedData.showAllUnmatched
    ? unmatchedData.unmatchedCounts.unmatched_grand_total_all === 0 &&
      unmatchedData.unmatchedCounts.grand_total_all > 0
    : unmatchedData.unmatchedCounts.unmatched_grand_total_with_file === 0 &&
      unmatchedData.unmatchedCounts.grand_total_with_file > 0;

  const assetsHasData =
    filePaths.movies.length > 0 ||
    filePaths.collections.length > 0 ||
    Object.keys(filePaths.shows).length > 0;

  const unmatchedHasData =
    unmatchedData.unmatchedMedia.movies.length > 0 ||
    unmatchedData.unmatchedMedia.collections.length > 0 ||
    unmatchedData.unmatchedMedia.shows.length > 0;

  const typeToFilter = {
    movies: "movies",
    collections: "collections",
    "series (main posters)": "shows",
    seasons: "shows",
    all: "all",
  };

  return (
    <div>
      <h1 className="mb-6 px-2 text-2xl font-bold text-white xl:px-0">
        Dashboard
      </h1>
      <div className="mx-2 flex flex-col rounded-lg bg-gray-800 py-2 md:flex-row xl:mx-0">
        {/* Left Navigation */}
        <nav className="w-full flex-shrink-0 border-gray-700 md:w-48 md:border-r">
          <ul className="flex flex-col overflow-x-auto text-sm md:flex-col md:overflow-x-visible">
            {sections.map((section) => {
              const Icon = section.icon;
              const isActive = activeSection === section.id;
              return (
                <li key={section.id} className="flex-shrink-0">
                  <button
                    onClick={() => {
                      setActiveSection(section.id);
                    }}
                    className={`relative flex w-full items-center gap-3 whitespace-nowrap p-2 text-left transition-colors ${
                      activeSection === section.id
                        ? "bg-gray-700 text-white"
                        : "text-gray-400 hover:bg-gray-700 hover:text-white"
                    }`}
                  >
                    <span
                      className={`absolute left-0 top-0 h-full w-1 rounded-r ${isActive ? "bg-blue-500" : "bg-transparent"}`}
                    />
                    <Icon size={20} />
                    <span className="flex-1">{section.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="flex-1 p-4 md:p-6">
          {/* Poster Viewer Sections */}
          <>
            <div className={activeSection === "poster-viewer" ? "" : "hidden"}>
              <div className="mb-6 flex flex-col gap-3 border-b border-gray-700 pb-4 sm:flex-row sm:items-start sm:justify-between lg:px-0">
                <div>
                  <h2 className="mb-2 text-xl font-semibold text-white">
                    Poster Viewer
                  </h2>
                  <p className="text-sm text-gray-400">View plex assets.</p>
                </div>
              </div>
              {assetsHasData ? (
                <div>
                  <PosterViewer />
                </div>
              ) : (
                <p className="text-sm text-gray-400">
                  Run poster renamerr to view assets.
                </p>
              )}
            </div>
          </>
          {/* Unmatched Stats Section */}
          <>
            <div
              className={activeSection === "unmatched-stats" ? "" : "hidden"}
            >
              <div className="mb-6 flex flex-col gap-3 border-b border-gray-700 pb-4 sm:flex-row sm:items-start sm:justify-between lg:px-0">
                <div>
                  <h2 className="mb-2 text-xl font-semibold text-white">
                    Unmatched Stats
                  </h2>
                  <p className="text-sm text-gray-400">View unmatched stats.</p>
                </div>
              </div>
              {unmatchedHasData || isComplete ? (
                <div>
                  <UnmatchedStats
                    onMissingClick={(type) => {
                      setUnmatchedFilter(typeToFilter[type] ?? "all");
                      setActiveSection("unmatched-assets");
                    }}
                  />
                </div>
              ) : (
                <p className="text-sm text-gray-400">
                  Run unmatched assets to view stats.
                </p>
              )}
            </div>
          </>
          {/* Unmatched Assets Section */}
          <>
            <div
              className={activeSection === "unmatched-assets" ? "" : "hidden"}
            >
              <div className="mb-6 flex flex-col gap-3 border-b border-gray-700 pb-4 sm:flex-row sm:items-start sm:justify-between lg:px-0">
                <div>
                  <h2 className="mb-2 text-xl font-semibold text-white">
                    Unmatched Assets
                  </h2>
                  <p className="text-sm text-gray-400">
                    View unmatched assets.
                  </p>
                </div>
              </div>
              {unmatchedHasData || isComplete ? (
                <div>
                  {isComplete ? (
                    <p className="mb-4 text-sm text-gray-400">
                      🎉 All media has posters — nothing unmatched!
                    </p>
                  ) : (
                    <UnmatchedAssets activeFilter={unmatchedFilter} />
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-400">
                  Run unmatched assets to view missing posters.
                </p>
              )}
            </div>
          </>
        </div>
      </div>
    </div>
  );
}

export default Home;
