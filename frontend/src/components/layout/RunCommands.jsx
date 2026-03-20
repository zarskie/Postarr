import { useEffect, useRef, useState } from "react";
import { ChevronUp, ChevronDown, Play, X } from "lucide-react";

const RunCommands = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedModule, setSelectedModule] = useState("");
  const [settings, setSettings] = useState({
    unmatchedAssets: false,
    unmatchedOnly: false,
    plexUpload: false,
    matchAltTitles: false,
    driveSync: false,
    reapplyPosters: false,
    showAllUnmatched: false,
    hideCollections: false,
  });
  const [logLevel, setLogLevel] = useState("info");
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState(null);
  const [jobRunning, setJobRunning] = useState(null);
  const pollRef = useRef(null);

  const fetchedModules = useRef(new Set());

  const handleToggle = () => {
    if (!isExpanded) {
      setIsExpanded(true);
    } else {
      setIsExpanded(false);
    }
  };

  const handleRun = async () => {
    if (!selectedModule) return;
    try {
      const endpointMap = {
        "poster-renamerr": "/api/poster-renamer/run-renamer-job",
        "plex-uploaderr": "/api/poster-renamer/run-plex-upload-job",
        "drive-sync": "/api/poster-renamer/run-drive-sync-job",
        "unmatched-assets": "/api/poster-renamer/run-unmatched-job",
      };
      const endpoint = endpointMap[selectedModule];
      if (!endpoint) return;
      const payload =
        selectedModule === "poster-renamerr"
          ? { settings: { ...settings, logLevel } }
          : selectedModule === "plex-uploaderr"
            ? {
                settings: { reapplyPosters: settings.reapplyPosters, logLevel },
              }
            : { settings: { logLevel } };
      setJobRunning(true);

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (result.success && result.job_id) {
        setJobId(result.job_id);
        setProgress(0);
        startPolling(result.job_id);
      } else if (!result.success) {
        setJobRunning(null);
        alert(result.message);
      }
    } catch (error) {
      setJobRunning(null);
      console.error("Error running command:", error);
    }
  };

  const startPolling = (id) => {
    pollRef.current = setInterval(async () => {
      try {
        const response = await fetch(`/api/poster-renamer/progress/${id}`);
        const result = await response.json();
        if (result.error) {
          clearInterval(pollRef.current);
          setJobId(null);
          setProgress(null);
          return;
        }
        setProgress(result.value);
        if (result.state === "completed" || result.value === 100) {
          clearInterval(pollRef.current);
          setJobRunning(null);
          setTimeout(() => {
            setJobId(null);
            setProgress(null);
          }, 2000);
        }
      } catch (error) {
        clearInterval(pollRef.current);
      }
    }, 1000);
  };

  useEffect(() => {
    return () => clearInterval(pollRef.current);
  }, []);

  useEffect(() => {
    if (!selectedModule) return;
    if (fetchedModules.current.has(selectedModule)) return;
    fetchedModules.current.add(selectedModule);

    const fetchSettings = async () => {
      try {
        const endpointMap = {
          "poster-renamerr": "/api/settings/get-poster-renamerr",
          "plex-uploaderr": "/api/settings/get-plex-uploaderr",
          "drive-sync": "/api/settings/get-drive-sync",
          "unmatched-assets": "/api/settings/get-unmatched-assets",
        };
        const endpoint = endpointMap[selectedModule];
        if (!endpoint) return;
        const response = await fetch(endpoint);
        const result = await response.json();
        if (result.success && result.data) {
          const d = result.data;
          if (selectedModule === "poster-renamerr") {
            setLogLevel(d.log_level ?? "info");
            setSettings((prev) => ({
              ...prev,
              unmatchedAssets: d.unmatched_assets ?? false,
              unmatchedOnly: d.unmatched_only ?? false,
              plexUpload: d.plex_upload ?? false,
              matchAltTitles: d.match_alt_titles ?? false,
              driveSync: d.drive_sync ?? false,
            }));
          }
          if (selectedModule === "plex-uploaderr") {
            setLogLevel(d.log_level ?? "info");
            setSettings((prev) => ({
              ...prev,
              reapplyPosters: d.reapply_posters ?? false,
            }));
          }
          if (selectedModule === "unmatched-assets") {
            setLogLevel(d.log_level ?? "info");
            setSettings((prev) => ({
              ...prev,
              showAllUnmatched: d.show_all_unmatched ?? false,
              hideCollections: d.hide_collections ?? false,
            }));
          }
          if (selectedModule === "drive-sync") {
            setLogLevel(d.log_level ?? "info");
          }
        }
      } catch (error) {
        console.error("Error fetching settings:", error);
      }
    };
    fetchSettings();
  }, [selectedModule]);

  return (
    <>
      <div
        className={`fixed bottom-0 left-0 right-0 z-50 flex flex-col justify-between overflow-hidden bg-gray-900 shadow-2xl transition-all duration-300 ease-in-out ${isExpanded ? "translate-y-0" : "translate-y-[calc(100%-3rem)]"}`}
      >
        {isExpanded && (
          <>
            <div className="mb-1 mt-2 flex items-start justify-between p-4">
              <div className="flex flex-col">
                <h3 className="mb-1 text-lg font-semibold text-white">
                  Command Execution
                </h3>
                <span className="text-xs text-gray-400">
                  These settings will override saved settings for this run
                </span>
              </div>
              <button
                onClick={handleToggle}
                className="rounded-md text-gray-400 transition-colors hover:text-white"
              >
                <X size={20} />
              </button>
            </div>
            <div className="flex flex-col border-t border-gray-800 2xl:flex-row">
              <div className="flex flex-col items-center 2xl:mb-2 2xl:flex-row">
                <div className="flex w-full flex-col px-4 py-2">
                  <span className="mb-2 text-xs font-medium text-gray-300">
                    Module
                  </span>
                  <div
                    className={`relative w-full 2xl:w-56 ${selectedModule ? "mb-0" : "mb-2"}`}
                  >
                    <select
                      value={selectedModule}
                      onChange={(e) => {
                        const newModule = e.target.value;
                        setSelectedModule(newModule);
                        setLogLevel("info");
                      }}
                      className="w-full appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 2xl:w-56"
                    >
                      <option value="">Choose a module</option>
                      <option value="poster-renamerr">Poster Renamerr</option>
                      <option value="unmatched-assets">Unmatched Assets</option>
                      <option value="plex-uploaderr">Plex Uploaderr</option>
                      <option value="drive-sync">Drive Sync</option>
                    </select>
                    <ChevronDown
                      size={18}
                      className="pointer-events-none absolute right-5 top-1/2 -translate-y-1/2 text-gray-400 2xl:right-2"
                    />
                  </div>
                </div>
                {selectedModule && (
                  <div className="flex w-full flex-col px-4 py-2">
                    <span className="mb-2 text-xs font-medium text-gray-300">
                      Log Level
                    </span>
                    <div className="relative w-full 2xl:w-56">
                      <select
                        value={logLevel}
                        onChange={(e) => {
                          setLogLevel(e.target.value);
                        }}
                        className="w-full appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 2xl:w-56"
                      >
                        <option value="info">Info</option>
                        <option value="debug">Debug</option>
                      </select>
                      <ChevronDown
                        size={18}
                        className="pointer-events-none absolute right-5 top-1/2 -translate-y-1/2 text-gray-400 2xl:right-2"
                      />
                    </div>
                  </div>
                )}
              </div>
              {selectedModule === "poster-renamerr" && (
                <>
                  <div className="mt-2 grid grid-cols-1 gap-y-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:ml-4 2xl:mt-6">
                    <div className="px-5 py-2">
                      <label className="flex cursor-pointer items-start gap-3">
                        <input
                          type="checkbox"
                          checked={settings.unmatchedAssets}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              unmatchedAssets: e.target.checked,
                            })
                          }
                          className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <div className="flex flex-col">
                          <span className="text-sm text-white">
                            Unmatched Assets
                          </span>
                          <span className="text-xs text-gray-400">
                            Run unmatched assets after poster renamerr
                          </span>
                        </div>
                      </label>
                    </div>
                    <div className="px-5 py-2">
                      <label className="flex cursor-pointer items-start gap-3">
                        <input
                          type="checkbox"
                          checked={settings.plexUpload}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              plexUpload: e.target.checked,
                            })
                          }
                          className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <div className="flex flex-col">
                          <span className="text-sm text-white">
                            Plex Upload
                          </span>
                          <span className="text-xs text-gray-400">
                            Run plex uploaderr after poster renamerr
                          </span>
                        </div>
                      </label>
                    </div>
                    <div className="px-5 py-2">
                      <label className="flex cursor-pointer items-start gap-3">
                        <input
                          type="checkbox"
                          checked={settings.driveSync}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              driveSync: e.target.checked,
                            })
                          }
                          className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <div className="flex flex-col">
                          <span className="text-sm text-white">Drive Sync</span>
                          <span className="text-xs text-gray-400">
                            Run drive sync before poster renamerr
                          </span>
                        </div>
                      </label>
                    </div>
                    <div className="px-5 py-2">
                      <label className="flex cursor-pointer items-start gap-3">
                        <input
                          type="checkbox"
                          checked={settings.unmatchedOnly}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              unmatchedOnly: e.target.checked,
                            })
                          }
                          className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <div className="flex flex-col">
                          <span className="text-sm text-white">
                            Unmatched Only
                          </span>
                          <span className="text-xs text-gray-400">
                            Run poster renamerr on only unmatched assets
                          </span>
                        </div>
                      </label>
                    </div>
                    <div className="px-5 py-2">
                      <label className="flex cursor-pointer items-start gap-3">
                        <input
                          type="checkbox"
                          checked={settings.matchAltTitles}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              matchAltTitles: e.target.checked,
                            })
                          }
                          className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <div className="flex flex-col">
                          <span className="text-sm text-white">
                            Match Alt Titles
                          </span>
                          <span className="text-xs text-gray-400">
                            Enable matching of alternate titles
                          </span>
                        </div>
                      </label>
                    </div>
                  </div>
                </>
              )}
              {selectedModule === "plex-uploaderr" && (
                <div className="mt-2 grid grid-cols-1 gap-y-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:ml-4 2xl:mt-6">
                  <div className="px-5 py-2">
                    <label className="flex cursor-pointer items-start gap-3">
                      <input
                        type="checkbox"
                        checked={settings.reapplyPosters}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            reapplyPosters: e.target.checked,
                          })
                        }
                        className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                      />
                      <div className="flex flex-col">
                        <span className="text-sm text-white">
                          Reapply Posters
                        </span>
                        <span className="text-xs text-gray-400">
                          Force re-upload posters in Plex
                        </span>
                      </div>
                    </label>
                  </div>
                </div>
              )}
              {selectedModule === "unmatched-assets" && (
                <div className="mt-2 grid grid-cols-1 gap-y-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:ml-4 2xl:mt-6">
                  <div className="px-5 py-2">
                    <label className="flex cursor-pointer items-start gap-3">
                      <input
                        type="checkbox"
                        checked={settings.showAllUnmatched}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            showAllUnmatched: e.target.checked,
                          })
                        }
                        className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                      />
                      <div className="flex flex-col">
                        <span className="text-sm text-white">
                          Show All Unmatched
                        </span>
                        <span className="text-xs text-gray-400">
                          Show unmatched assets for missing media
                        </span>
                      </div>
                    </label>
                  </div>
                  <div className="px-5 py-2">
                    <label className="flex cursor-pointer items-start gap-3">
                      <input
                        type="checkbox"
                        checked={settings.hideCollections}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            hideCollections: e.target.checked,
                          })
                        }
                        className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                      />
                      <div className="flex flex-col">
                        <span className="text-sm text-white">
                          Hide Collections
                        </span>
                        <span className="text-xs text-gray-400">
                          Hide collections from unmatched assets
                        </span>
                      </div>
                    </label>
                  </div>
                </div>
              )}
              {selectedModule && (
                <div className="mb-2 mt-2 flex w-full self-end px-4 py-2 lg:ml-auto lg:w-auto">
                  <button
                    className="flex w-full items-center justify-center gap-2 whitespace-nowrap rounded-md bg-blue-600 px-2 py-1.5 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={handleRun}
                    disabled={jobRunning}
                  >
                    <Play size={14} />
                    {jobRunning ? "Running..." : "Run commands"}
                  </button>
                </div>
              )}
            </div>
          </>
        )}
        <div className="flex shrink-0 items-center border-t border-gray-800 py-2">
          <button
            onClick={handleToggle}
            className="flex items-center gap-2 rounded-md px-4 py-2 text-sm text-gray-400 transition-colors hover:text-white"
          >
            {isExpanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
            <span className="text-xs font-medium uppercase tracking-wide">
              Run Commands
            </span>
          </button>
        </div>
        {jobId && progress !== null && (
          <div className="px-4 py-2">
            <div className="h-1.5 w-full rounded-full bg-gray-700">
              <div
                className="h-1.5 rounded-full bg-blue-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="mt-1 text-xs text-gray-400">{progress}%</span>
          </div>
        )}
      </div>
    </>
  );
};
export default RunCommands;
