import { ChevronDown } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useUnmatched } from "../../context/UnmatchedContext";

const UnmatchedAssetsSettings = ({ onDirtyChange }) => {
  const [logLevel, setLogLevel] = useState("info");
  const [isLoading, setIsLoading] = useState(false);
  const [settings, setSettings] = useState({
    showAllUnmatched: false,
    hideCollections: false,
  });
  const [initialState, setInitialState] = useState(null);
  const { refreshUnmatchedData, unmatchedData } = useUnmatched();

  const hasCountData =
    unmatchedData.unmatchedCounts.grand_total_all > 0 ||
    unmatchedData.unmatchedCounts.grand_total_with_file > 0;

  const unmatchedHasData =
    unmatchedData.unmatchedMedia.movies.length > 0 ||
    unmatchedData.unmatchedMedia.collections.length > 0 ||
    unmatchedData.unmatchedMedia.shows.length > 0;

  const canReset = hasCountData || unmatchedHasData;

  const handleSave = async () => {
    setIsLoading(true);
    try {
      const payload = {
        logLevel: logLevel.trim(),
        settings: {
          showAllUnmatched: settings.showAllUnmatched,
          hideCollections: settings.hideCollections,
        },
      };
      const response = await fetch("/api/settings/save-unmatched-assets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (response.ok) {
        setInitialState({
          logLevel: logLevel.trim(),
          settings: { ...settings },
        });
        refreshUnmatchedData();
      } else {
        alert(`Failed!: ${result.message}`);
      }
    } catch (error) {
      console.error("Error saving settings:", error);
    } finally {
      setIsLoading(false);
    }
  };
  const handleReset = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/settings/reset-unmatched-data", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
      });
      const data = await response.json();
      if (data.success) {
        refreshUnmatchedData();
      } else {
        console.error("Failed to reset unmatched data:", data.message);
      }
    } catch (error) {
      console.error("Error resetting unmatched data:", error);
    } finally {
      setIsLoading(false);
    }
  };
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch("/api/settings/get-unmatched-assets");
        const result = await response.json();
        if (result.success && result.data) {
          const d = result.data;
          setLogLevel(d.log_level || "info");
          setSettings({
            hideCollections: d.hide_collections || false,
            showAllUnmatched: d.show_all_unmatched || false,
          });
          if (d.is_configured) {
            setInitialState({
              logLevel: d.log_level || "info",
              settings: {
                hideCollections: d.hide_collections || false,
                showAllUnmatched: d.show_all_unmatched || false,
              },
            });
          }
        }
      } catch (error) {
        console.error("Error fetching settings:", error);
      }
    };
    fetchSettings();
  }, []);

  const hasChanges = useMemo(() => {
    if (!initialState) return false;
    return (
      logLevel !== initialState.logLevel ||
      JSON.stringify(settings) !== JSON.stringify(initialState.settings)
    );
  }, [initialState, logLevel, settings]);

  useEffect(() => {
    onDirtyChange?.(hasChanges);
  }, [hasChanges, onDirtyChange]);

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-white">
        Unmatched Assets
      </h2>
      <div className="mb-4 rounded-lg bg-gray-700 p-4">
        <div className="mb-2 flex flex-col border-b border-gray-600 pb-4">
          <h2 className="mb-2 text-sm font-medium text-white">Log Level</h2>
          <div className="relative">
            <select
              value={logLevel}
              onChange={(e) => {
                setLogLevel(e.target.value);
              }}
              className="w-full appearance-none rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="info">Info</option>
              <option value="debug">Debug</option>
            </select>
            <ChevronDown
              size={18}
              className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-x-2 gap-y-6 border-b border-gray-600 py-5 lg:grid-cols-2">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.showAllUnmatched}
              onChange={(e) =>
                setSettings({ ...settings, showAllUnmatched: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Show All Unmatched</span>
              <span className="text-xs text-gray-400">
                Show unmatched assets for missing media
              </span>
            </div>
          </label>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.hideCollections}
              onChange={(e) =>
                setSettings({ ...settings, hideCollections: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Hide Collections</span>
              <span className="text-xs text-gray-400">
                Hide collections from unmatched assets
              </span>
            </div>
          </label>
        </div>
        <div className="mt-4 flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
          <button
            onClick={handleSave}
            disabled={isLoading || (initialState !== null && !hasChanges)}
            className="flex w-full items-center justify-center self-start rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            {isLoading
              ? "Saving..."
              : initialState !== null && !hasChanges
                ? "No Changes"
                : "Save"}
          </button>
          <button
            onClick={handleReset}
            disabled={isLoading || !canReset}
            className="flex w-full items-center justify-center self-start rounded-md bg-red-700 px-4 py-2 text-sm text-white transition-colors hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            {isLoading
              ? "Resetting..."
              : !canReset
                ? "Nothing to reset"
                : "Reset data"}
          </button>
        </div>
      </div>
    </div>
  );
};
export default UnmatchedAssetsSettings;
