import { useState, useEffect, useRef } from "react";
import useDebounce from "../hooks/debounce";
import { createPortal } from "react-dom";
import { CircleQuestionMark } from "lucide-react";

function PosterSearch() {
  const tooltipTimeout = useRef(null);
  const [activeTooltip, setActiveTooltip] = useState(null);
  const [status, setStatus] = useState(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hoveredIndex, setHoveredIndex] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const debouncedQuery = useDebounce(query, 300);
  const [folderFilters, setFolderFilters] = useState({
    all: true,
    enabled: false,
    priority: false,
  });
  const showToolTip = (name) => {
    clearTimeout(tooltipTimeout.current);
    setActiveTooltip(name);
  };
  const hideTooltip = () => {
    tooltipTimeout.current = setTimeout(() => {
      setActiveTooltip(null);
    }, 300);
  };

  const cancelHide = () => {
    clearTimeout(tooltipTimeout.current);
  };

  const handleResetCache = async () => {
    setStatus("loading");
    await fetch("/api/poster-search/reset-cache", { method: "PUT" });
    setStatus("done");
    setTimeout(() => setStatus(null), 2000);
  };

  useEffect(() => {
    if (debouncedQuery.length < 3) {
      setResults([]);
      setTotal(0);
      return;
    }
    const getFilterMode = (() => {
      if (folderFilters.all)
        return folderFilters.priority ? "priority_all" : "all";
      if (folderFilters.enabled)
        return folderFilters.priority ? "priority" : "enabled";
      return folderFilters.priority ? "priority_all" : "all";
    })();

    const fetchResults = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `/api/poster-search/search?q=${encodeURIComponent(debouncedQuery)}&filter=${getFilterMode}`
        );
        const data = await res.json();
        setResults(data.results);
        setTotal(data.total);
      } catch (err) {
        console.error("Search failed:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
  }, [debouncedQuery, folderFilters]);

  useEffect(() => {
    const handleScroll = () => setHoveredIndex(null);
    window.addEventListener("scroll", handleScroll, true);
    return () => window.removeEventListener("scroll", handleScroll, true);
  }, []);

  return (
    <div className="flex max-h-[750px] w-full flex-col gap-1 rounded-lg bg-gray-900 p-4">
      <div className="flex flex-col gap-2">
        <input
          className="w-full rounded border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Search posters..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="mt-1 flex items-center gap-3">
          <div className="flex gap-2">
            <label className="flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={folderFilters.all}
                onChange={(e) =>
                  setFolderFilters((prev) => ({
                    ...prev,
                    all: e.target.checked,
                    enabled: e.target.checked ? false : true,
                  }))
                }
                className="h-3 w-3 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
              />
            </label>
            <div className="relative flex items-center gap-1">
              <span className="text-xs text-gray-400">all folders</span>
              <CircleQuestionMark
                size={14}
                className="text-gray-400 hover:text-white"
                onMouseEnter={() => showToolTip("allFolders")}
                onMouseLeave={hideTooltip}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveTooltip(
                    activeTooltip === "allFolders" ? null : "allFolders"
                  );
                }}
              />
              {activeTooltip === "allFolders" && (
                <div
                  className="absolute left-1/2 top-full z-10 mt-1 w-auto -translate-x-1/3 whitespace-nowrap rounded-md border border-gray-700 bg-gray-800 px-2 py-2 text-xs text-gray-300 shadow-lg"
                  onMouseEnter={cancelHide}
                  onMouseLeave={hideTooltip}
                >
                  <span className="text-xs text-gray-300">
                    Search all drives in drive directory
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <label className="flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={folderFilters.enabled}
                onChange={(e) =>
                  setFolderFilters((prev) => ({
                    ...prev,
                    enabled: e.target.checked,
                    all: e.target.checked ? false : true,
                  }))
                }
                className="h-3 w-3 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
              />
            </label>
            <div className="relative flex items-center gap-1">
              <span className="text-xs text-gray-400">enabled folders</span>
              <CircleQuestionMark
                size={14}
                className="text-gray-400 hover:text-white"
                onMouseEnter={() => showToolTip("enabledFolders")}
                onMouseLeave={hideTooltip}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveTooltip(
                    activeTooltip === "enabledFolders" ? null : "enabledFolders"
                  );
                }}
              />
              {activeTooltip === "enabledFolders" && (
                <div
                  className="absolute left-1/2 top-full z-10 mt-1 w-auto -translate-x-1/3 whitespace-nowrap rounded-md border border-gray-700 bg-gray-800 px-2 py-2 text-xs text-gray-300 shadow-lg"
                  onMouseEnter={cancelHide}
                  onMouseLeave={hideTooltip}
                >
                  <span className="text-xs text-gray-300">
                    Search only drives configured in poster renamerr
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <label className="flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={folderFilters.priority}
                onChange={(e) =>
                  setFolderFilters((prev) => ({
                    ...prev,
                    priority: e.target.checked,
                  }))
                }
                className="h-3 w-3 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
              />
            </label>
            <div className="relative flex items-center gap-1">
              <span className="text-xs text-gray-400">priority</span>
              <CircleQuestionMark
                size={14}
                className="text-gray-400 hover:text-white"
                onMouseEnter={() => showToolTip("priority")}
                onMouseLeave={hideTooltip}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveTooltip(
                    activeTooltip === "priority" ? null : "priority"
                  );
                }}
              />
              {activeTooltip === "priority" && (
                <div
                  className="absolute left-1/2 top-full z-10 mt-1 w-40 -translate-x-1/3 rounded-md border border-gray-700 bg-gray-800 px-2 py-2 text-xs text-gray-300 shadow-lg sm:w-auto sm:whitespace-nowrap"
                  onMouseEnter={cancelHide}
                  onMouseLeave={hideTooltip}
                >
                  <span className="text-xs text-gray-300">
                    Sort results by poster renamerr drive priority
                  </span>
                </div>
              )}
            </div>
          </div>
          <button
            disabled={status === "loading"}
            className={`ml-auto w-24 rounded-full border px-2 py-0.5 text-xs text-white transition-colors duration-300 disabled:opacity-50 ${status === "done" ? "border-green-700 bg-green-600" : "border-blue-700 bg-blue-600 hover:bg-blue-700"}`}
            onClick={handleResetCache}
          >
            {status === "loading"
              ? "resetting..."
              : status === "done"
                ? "✓ done"
                : "reset cache"}
          </button>
        </div>
      </div>
      {loading && <p className="mt-1 text-xs text-gray-500">Searching...</p>}
      {!loading && total > 100 && (
        <p className="mt-1 text-xs text-gray-500">
          Showing 100 of {total} results
        </p>
      )}
      {!loading && results.length > 0 && (
        <>
          <p className="mt-1 text-xs text-gray-600">
            {total} result{total !== 1 ? "s" : ""}
          </p>
          <ul className="mt-1 flex min-w-0 flex-col gap-1 overflow-y-auto border-gray-700 px-3 py-1">
            {results.map((r, i) => (
              <li
                key={i}
                className="mb-1 flex gap-3 border-l-2 px-2 py-1 transition-colors hover:border-blue-500"
              >
                <img
                  src={`/api/poster-search/serve-image?path=${encodeURIComponent(r.full_path)}`}
                  loading="lazy"
                  className="h-16 w-11 flex-shrink-0 origin-left rounded object-contain"
                  onMouseEnter={(e) => {
                    setHoveredIndex(i);
                    setMousePos({ x: e.clientX, y: e.clientY });
                  }}
                  onMouseMove={(e) =>
                    setMousePos({ x: e.clientX, y: e.clientY })
                  }
                  onMouseLeave={() => setHoveredIndex(null)}
                />
                <div className="flex flex-col justify-center gap-1">
                  <span
                    className="break-words text-sm text-gray-200"
                    title={r.filename.replace(/\.[^/.]+$/, "")}
                  >
                    {r.filename.replace(/\.[^/.]+$/, "")}
                  </span>
                  <span className="mb-1 w-fit rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-400">
                    {r.path}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      {hoveredIndex !== null &&
        createPortal(
          <img
            src={`/api/poster-search/serve-image?path=${encodeURIComponent(results[hoveredIndex].full_path)}`}
            className="shadowxl pointer-events-none fixed z-50 h-64 w-44 rounded object-contain"
            style={{
              top:
                window.innerWidth < 640 &&
                mousePos.y + 16 + 256 > window.innerHeight
                  ? mousePos.y - 256 - 16
                  : mousePos.y + 16,
              left: mousePos.x + 16,
            }}
          />,
          document.body
        )}
    </div>
  );
}
export default PosterSearch;
