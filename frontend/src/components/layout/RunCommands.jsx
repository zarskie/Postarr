import { useEffect, useRef, useState } from "react";
import { ChevronUp, ChevronDown, Play, X } from "lucide-react";
import { usePoster } from "../../context/PosterContext";
import FieldError from "../common/FieldError";
import { useUnmatched } from "../../context/UnmatchedContext";
import { isValidHex } from "../utils/validators";

const RunCommands = () => {
  const jobRunningRef = useRef(false);
  const { refreshFilePaths, bustPreview } = usePoster();
  const { refreshUnmatchedData } = useUnmatched();
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedModule, setSelectedModule] = useState("");
  const [settings, setSettings] = useState({
    unmatchedAssets: false,
    unmatchedOnly: false,
    plexUpload: false,
    matchAltTitles: false,
    driveSync: false,
    reapplyPosters: false,
    borderSetting: "",
    customColor: "",
  });
  const [logLevel, setLogLevel] = useState("info");
  const [version, setVersion] = useState("");
  const [build, setBuild] = useState("");
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [jobs, setJobs] = useState({});
  const [jobRunning, setJobRunning] = useState(null);
  const [errors, setErrors] = useState({});
  const [popupField, setPopupField] = useState(null);
  const [blurredFields, setBlurredFields] = useState(new Set());
  const pollRef = useRef(null);
  const borderSettingRef = useRef(null);
  const customColorRef = useRef(null);
  const activeJob = Object.entries(jobs)[0] ?? null;

  const fetchedModules = useRef(new Set());

  const handleToggle = () => {
    if (!isExpanded) {
      setIsExpanded(true);
      setErrors({});
      setBlurredFields(new Set());
    } else {
      setIsExpanded(false);
      setErrors({});
      setBlurredFields(new Set());
    }
  };

  const handleRun = async () => {
    if (!selectedModule) return;

    if (selectedModule === "border-replacerr") {
      const newErrors = {};
      if (!settings.borderSetting)
        newErrors.borderSetting = "Please select an option";
      if (settings.borderSetting && settings.borderSetting === "custom") {
        if (!settings.customColor || !isValidHex(settings.customColor))
          newErrors.customColor =
            "Please enter a valid hex color (e.g. #ff0000)";
      }
      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors);
        if (newErrors.borderSetting) {
          setPopupField("borderSetting");
          borderSettingRef.current?.focus();
        } else if (newErrors.customColor) {
          setPopupField("customColor");
          customColorRef.current?.focus();
        }
        return;
      }
    }

    setErrors({});
    try {
      const endpointMap = {
        "poster-renamerr": "/api/poster-renamer/run-renamer-job",
        "plex-uploaderr": "/api/poster-renamer/run-plex-upload-job",
        "drive-sync": "/api/poster-renamer/run-drive-sync-job",
        "unmatched-assets": "/api/poster-renamer/run-unmatched-job",
        "border-replacerr": "/api/poster-renamer/run-border-replace-job",
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
            : selectedModule === "border-replacerr"
              ? {
                  settings: {
                    borderSetting: settings.borderSetting,
                    customColor: settings.customColor,
                    logLevel,
                  },
                }
              : { settings: { logLevel } };
      setJobRunning(true);

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (result.success && !result.job_id) {
        setJobRunning(null);
        alert(result.message);
      } else if (result.success) {
        setErrors({});
        jobRunningRef.current = true;
        setJobRunning(true);
        startPolling();
      } else {
        setJobRunning(null);
        alert(result.message);
      }
    } catch (error) {
      setJobRunning(null);
      console.error("Error running command:", error);
    }
  };

  const startPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const response = await fetch(`/api/poster-renamer/progress`);
        const result = await response.json();
        setJobs(result);
        if (Object.keys(result).length === 0 && jobRunningRef.current) {
          clearInterval(pollRef.current);
          jobRunningRef.current = false;
          setJobRunning(null);
          setTimeout(() => {
            refreshFilePaths();
            refreshUnmatchedData();
            bustPreview();
          }, 2000);
        }
      } catch (error) {
        clearInterval(pollRef.current);
        console.error("Error polling progress:", error);
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
          "border-replacerr": "/api/settings/get-border-replacerr",
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
          if (selectedModule === "border-replacerr") {
            setLogLevel(d.log_level ?? "info");
            setSettings((prev) => ({
              ...prev,
              borderSetting: d.border_setting ?? "",
              customColor: d.custom_color ?? "",
            }));
          }
          if (selectedModule === "unmatched-assets") {
            setLogLevel(d.log_level ?? "info");
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

  useEffect(() => {
    fetch("/api/settings/version")
      .then((res) => res.json())
      .then((data) => {
        setVersion(data.version);
        setBuild(data.build_number);
      });
  }, []);

  useEffect(() => {
    fetch("/api/settings/check-update")
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setUpdateAvailable(data.update_available);
        }
      })
      .catch((err) => console.error("Failed to check for updates:", err));
  }, []);

  return (
    <>
      <div
        className={`fixed bottom-0 left-0 right-0 z-50 flex flex-col justify-between overflow-hidden bg-gray-900 shadow-2xl transition-all duration-300 ease-in-out ${isExpanded ? "translate-y-0" : Object.keys(jobs).length > 0 ? "translate-y-[calc(100%-6rem)]" : "translate-y-[calc(100%-3rem)]"}`}
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
            <div className="flex flex-col border-t border-gray-800 py-2 2xl:flex-row 2xl:items-start">
              <div className="flex flex-col items-center 2xl:mb-2 2xl:flex-row">
                <div className="flex w-full flex-col px-4 py-2">
                  <span className="mb-2 text-xs font-medium text-gray-300">
                    Module
                  </span>
                  <div className="relative w-full 2xl:w-56">
                    <select
                      value={selectedModule}
                      onChange={(e) => {
                        const newModule = e.target.value;
                        setSelectedModule(newModule);
                        setErrors({});
                        setBlurredFields(new Set());
                        setLogLevel("info");
                      }}
                      className="w-full appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 2xl:w-56"
                    >
                      <option value="">Choose a module</option>
                      <option value="poster-renamerr">Poster Renamerr</option>
                      <option value="unmatched-assets">Unmatched Assets</option>
                      <option value="plex-uploaderr">Plex Uploaderr</option>
                      <option value="drive-sync">Drive Sync</option>
                      <option value="border-replacerr">Border Replacerr</option>
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
                        <option value="trace">Trace</option>
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
              {selectedModule === "border-replacerr" && (
                <>
                  <div className="flex flex-col 2xl:flex-row">
                    <div className="flex w-full flex-col px-4 py-2">
                      <span className="mb-2 text-xs font-medium text-gray-300">
                        Border Type
                        <span className="text-xs font-medium text-red-500">
                          {" "}
                          *
                        </span>
                      </span>
                      <div className="relative w-full 2xl:w-56">
                        <select
                          value={settings.borderSetting}
                          ref={borderSettingRef}
                          onChange={(e) => {
                            setSettings({
                              ...settings,
                              borderSetting: e.target.value,
                              customColor: "",
                            });
                            if (
                              blurredFields.has("borderSetting") ||
                              errors.borderSetting
                            ) {
                              if (e.target.value.trim()) {
                                setErrors((prev) => ({
                                  ...prev,
                                  borderSetting: null,
                                }));
                              } else {
                                setErrors((prev) => ({
                                  ...prev,
                                  borderSetting: true,
                                }));
                              }
                            }
                          }}
                          onBlur={() => {
                            setPopupField(null);
                            if (errors.borderSetting) {
                              setBlurredFields((prev) =>
                                new Set(prev).add("borderSetting")
                              );
                            }
                          }}
                          className={`w-full appearance-none rounded-md border bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 2xl:w-56 ${blurredFields.has("borderSetting") && errors.borderSetting ? "border-red-500 focus:ring-red-500" : "border-gray-700 focus:ring-blue-500"}`}
                        >
                          <option value="">Select border type</option>
                          <option value="remove">Remove</option>
                          <option value="black">Black</option>
                          <option value="custom">Custom</option>
                        </select>
                        <ChevronDown
                          size={18}
                          className="pointer-events-none absolute right-5 top-1/2 -translate-y-1/2 text-gray-400 2xl:right-2"
                        />
                        {popupField === "borderSetting" &&
                          errors.borderSetting && (
                            <div className="absolute z-10 w-full">
                              <FieldError message={errors.borderSetting} />
                            </div>
                          )}
                      </div>
                      <div className="min-h-[1rem]">
                        {blurredFields.has("borderSetting") &&
                          errors.borderSetting && (
                            <span className="text-xs text-red-500">
                              Required
                            </span>
                          )}
                      </div>
                    </div>
                    {settings.borderSetting === "custom" && (
                      <div className="flex w-full flex-col px-4 py-2">
                        <span className="mb-2 text-xs font-medium text-gray-300">
                          Hex Code
                          <span className="text-xs font-medium text-red-500">
                            {" "}
                            *
                          </span>
                        </span>
                        <div className="relative w-full 2xl:w-56">
                          <input
                            type="text"
                            value={settings.customColor}
                            ref={customColorRef}
                            onChange={(e) => {
                              setSettings({
                                ...settings,
                                customColor: e.target.value,
                              });
                              if (
                                blurredFields.has("customColor") ||
                                errors.customColor
                              ) {
                                if (isValidHex(e.target.value)) {
                                  setErrors((prev) => ({
                                    ...prev,
                                    customColor: null,
                                  }));
                                  setPopupField(null);
                                } else {
                                  setErrors((prev) => ({
                                    ...prev,
                                    customColor:
                                      "Please enter a valid hex color (e.g. #ff0000)",
                                  }));
                                }
                              }
                            }}
                            onBlur={() => {
                              if (errors.customColor) {
                                setBlurredFields((prev) =>
                                  new Set(prev).add("customColor")
                                );
                              }
                            }}
                            className={`w-full appearance-none rounded-md border bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 2xl:w-56 ${blurredFields.has("customColor") && errors.customColor ? "border-red-500 focus:ring-red-500" : "border-gray-700 focus:ring-blue-500"}`}
                            placeholder="#000000"
                          />
                          {popupField === "customColor" &&
                            errors.customColor && (
                              <div className="absolute z-10 w-full">
                                <FieldError message={errors.customColor} />
                              </div>
                            )}
                        </div>
                        <div className="min-h-[1rem]">
                          {blurredFields.has("customColor") &&
                            errors.customColor && (
                              <span className="text-xs text-red-500">
                                Required
                              </span>
                            )}
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
              {selectedModule && (
                <div className="flex w-full self-end px-4 py-2 lg:ml-auto lg:w-auto">
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
        <div className="flex shrink-0 items-center justify-between border-t border-gray-800 py-2">
          <button
            onClick={handleToggle}
            className="flex items-center gap-2 rounded-md px-4 py-2 text-sm text-gray-400 transition-colors hover:text-white"
          >
            {isExpanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
            <span className="text-xs font-medium uppercase tracking-wide">
              Run Commands
            </span>
          </button>
          <div className="flex items-center">
            <a
              className={`rounded-full border border-blue-700 bg-blue-600 px-4 py-1 text-xs font-medium text-white hover:bg-blue-700 ${updateAvailable ? "" : "hidden"}`}
              href="https://github.com/zarskie/Postarr/releases"
              target="_blank"
              rel="noopener noreferrer"
            >
              Update Available
            </a>
            <span className="px-4 py-1 text-xs font-medium text-gray-400">
              Postarr v{version}
              {build ? `.${build}` : ""}
            </span>
          </div>
        </div>
        <div
          className={`overflow-hidden transition-all duration-300 ease-in-out ${activeJob ? "max-h-20" : "max-h-0"}`}
        >
          <div className="px-4 py-2">
            <div className="mb-0.5 flex justify-between">
              <span className="text-xs text-gray-400">{activeJob?.[0]}</span>
              <span className="text-xs text-gray-400">
                {activeJob?.[1].state}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-gray-700">
              <div
                className="h-1.5 rounded-full bg-blue-500 transition-all duration-300"
                style={{
                  width: `${activeJob?.[1].value ?? 0}%`,
                  background:
                    activeJob?.[1].state === "Failed"
                      ? "#ef4444"
                      : "linear-gradient(to right, #3b82f6, #8b5cf6)",
                }}
              />
            </div>
            <span className="mt-1 text-xs text-gray-400">
              {activeJob?.[1].value ?? 0}%
            </span>
          </div>
        </div>
      </div>
    </>
  );
};
export default RunCommands;
