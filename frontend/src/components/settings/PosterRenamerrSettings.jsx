import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
  Plus,
  X,
  Check,
  Info,
} from "lucide-react";
import FieldError from "../common/FieldError";
import { isValidHex } from "../utils/validators";

const PosterRenamerrSettings = ({ onDirtyChange }) => {
  const posterRootRef = useRef(null);
  const assetDirectoryRef = useRef(null);
  const sourceFoldersRef = useRef(null);
  const librariesRef = useRef(null);
  const customHexRef = useRef(null);
  const borderTypeRef = useRef(null);
  const tooltipTimeout = useRef(null);
  const [logLevel, setLogLevel] = useState([""]);
  const [sourceFolders, setSourceFolders] = useState([""]);
  const [isReorderMode, setIsReorderMode] = useState(false);
  const [libraries, setLibraries] = useState([""]);
  const [settings, setSettings] = useState({
    assetFolders: false,
    cleanAssets: false,
    unmatchedAssets: false,
    replaceBorder: false,
    webhookRun: false,
    unmatchedOnly: false,
    plexUpload: false,
    matchAltTitles: false,
    driveSync: false,
  });
  const [borderType, setBorderType] = useState("");
  const [customHex, setCustomHex] = useState("");
  const [posterRoot, setPosterRoot] = useState("");
  const [assetDirectory, setAssetDirectory] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [popupField, setPopupField] = useState(null);
  const [blurredFields, setBlurredFields] = useState(new Set());
  const [initialState, setInitialState] = useState(null);
  const [fetchLibrariesError, setFetchLibrariesError] = useState(null);
  const [fetchFoldersError, setFetchFoldersError] = useState(null);
  const [reorderValues, setReorderValues] = useState({});
  const [folderFilters, setFolderFilters] = useState({
    mm2k: false,
    cl2k: false,
  });
  const [showAllFolders, setShowAllFolders] = useState(false);
  const [activeTooltip, setActiveTooltip] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const FOLDERS_PREVIEW = 5;

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

  const addFolder = () => {
    setSourceFolders([...sourceFolders, ""]);
    setShowAllFolders(true);
  };
  const removeFolder = (index) => {
    setSourceFolders(sourceFolders.filter((_, i) => i !== index));
  };
  const updateFolder = (index, value) => {
    const newFolders = [...sourceFolders];
    newFolders[index] = value;
    setSourceFolders(newFolders);
  };

  const addLibrary = () => {
    setLibraries([...libraries, ""]);
  };

  const removeLibrary = (index) => {
    setLibraries(libraries.filter((_, i) => i !== index));
  };

  const updateLibrary = (index, value) => {
    const newLibraries = [...libraries];
    newLibraries[index] = value;
    setLibraries(newLibraries);
  };
  const moveUp = (index) => {
    if (index === 0) return;
    const newFolders = [...sourceFolders];
    [newFolders[index - 1], newFolders[index]] = [
      newFolders[index],
      newFolders[index - 1],
    ];
    setSourceFolders(newFolders);
  };
  const moveDown = (index) => {
    if (index === sourceFolders.length - 1) return;
    const newFolders = [...sourceFolders];
    [newFolders[index], newFolders[index + 1]] = [
      newFolders[index + 1],
      newFolders[index],
    ];
    setSourceFolders(newFolders);
  };

  const handleFetchFolders = async () => {
    if (!posterRoot) {
      setErrors((prev) => ({ ...prev, posterRoot: true }));
      setPopupField("posterRoot");
      posterRootRef.current?.focus();
      return;
    }
    try {
      const response = await fetch(
        `/api/settings/get-source-folders?posterRoot=${encodeURIComponent(posterRoot)}`,
      );
      const result = await response.json();
      if (result.success && result.folders.length > 0) {
        setFetchFoldersError(null);
        let filtered = result.folders;
        if (folderFilters.mm2k)
          filtered = filtered.filter((f) => f.includes("mm2k"));
        if (folderFilters.cl2k)
          filtered = filtered.filter((f) => f.includes("cl2k"));
        setShowAllFolders(true);
        setSourceFolders((prev) => {
          const existing = prev.filter((l) => l.trim() !== "");
          const newFolders = filtered.filter((f) => !existing.includes(f));
          return existing.length > 0 || newFolders.length > 0
            ? [...existing, ...newFolders]
            : [""];
        });
      } else {
        setFetchFoldersError(result.message);
      }
    } catch (error) {
      console.error("Error fetching libraries:", error);
    }
  };
  const handleFetchLibraries = async () => {
    try {
      const response = await fetch("/api/settings/get-plex-libraries");
      const result = await response.json();
      if (result.success && result.libraries.length > 0) {
        setFetchLibrariesError(null);
        setLibraries((prev) => {
          const existing = prev.filter((l) => l.trim() !== "");
          const newLibraries = result.libraries.filter(
            (l) => !existing.includes(l),
          );
          return existing.length > 0 || newLibraries.length > 0
            ? [...existing, ...newLibraries]
            : [""];
        });
      } else {
        setFetchLibrariesError(result.message);
      }
    } catch (error) {
      console.error("Error fetching libraries:", error);
    }
  };

  const handleSave = async () => {
    const validSourceFolders = sourceFolders.filter((f) => f.trim() !== "");
    const validLibraries = libraries.filter((f) => f.trim() !== "");
    if (isReorderMode) setIsReorderMode(false);

    const newErrors = {};
    if (!posterRoot) newErrors.posterRoot = true;
    if (!assetDirectory) newErrors.assetDirectory = true;
    if (validSourceFolders.length === 0) newErrors.sourceFolders = true;
    if (validLibraries.length === 0) newErrors.libraries = true;
    if (settings.replaceBorder && !borderType)
      newErrors.borderType = "Please select an option";
    if (settings.replaceBorder && borderType === "custom") {
      if (!customHex || !isValidHex(customHex))
        newErrors.customHex = "Please enter a valid hex color (e.g. #ff0000)";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      if (newErrors.posterRoot) {
        setPopupField("posterRoot");
        posterRootRef.current?.focus();
      } else if (newErrors.assetDirectory) {
        setPopupField("assetDirectory");
        assetDirectoryRef.current?.focus();
      } else if (newErrors.sourceFolders) {
        setPopupField("sourceFolders");
        sourceFoldersRef.current?.focus();
      } else if (newErrors.libraries) {
        setPopupField("libraries");
        librariesRef.current?.focus();
      } else if (newErrors.borderType) {
        setPopupField("borderType");
        borderTypeRef.current?.focus();
      } else if (newErrors.customHex) {
        setPopupField("customHex");
        customHexRef.current?.focus();
      }
      return;
    }

    setErrors({});
    setIsLoading(true);
    try {
      const payload = {
        logLevel: logLevel.trim(),
        posterRoot: posterRoot.trim(),
        assetDirectory: assetDirectory.trim(),
        sourceFolders: validSourceFolders.map((f) => f.trim()),
        libraries: validLibraries.map((f) => f.trim()),
        settings: {
          assetFolders: settings.assetFolders,
          cleanAssets: settings.cleanAssets,
          unmatchedAssets: settings.unmatchedAssets,
          replaceBorder: settings.replaceBorder,
          webhookRun: settings.webhookRun,
          unmatchedOnly: settings.unmatchedOnly,
          plexUpload: settings.plexUpload,
          matchAltTitles: settings.matchAltTitles,
          driveSync: settings.driveSync,
        },
        borderType: settings.replaceBorder ? borderType : null,
        customHex:
          settings.replaceBorder && borderType == "custom"
            ? customHex.trim()
            : null,
      };
      const response = await fetch("/api/settings/save-poster-renamerr", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (response.ok) {
        setErrors({});
        setBlurredFields(new Set());
        setInitialState({
          logLevel: logLevel.trim(),
          posterRoot: posterRoot.trim(),
          assetDirectory: assetDirectory.trim(),
          sourceFolders: validSourceFolders.map((f) => f.trim()),
          libraries: validLibraries.map((f) => f.trim()),
          settings: { ...settings },
          borderType: settings.replaceBorder ? borderType : "",
          customHex:
            settings.replaceBorder && borderType === "custom"
              ? customHex.trim()
              : "",
        });
      } else {
        alert(`Failed!: ${result.message}`);
      }
    } catch (error) {
      console.error("Error saving settings:", error);
      alert("Error connecting to server");
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }

    setLogLevel("info");
    setPosterRoot("");
    setAssetDirectory("");
    setSourceFolders([""]);
    setLibraries([""]);
    setSettings({
      assetFolders: false,
      cleanAssets: false,
      unmatchedAssets: false,
      webhookRun: false,
      unmatchedOnly: false,
      plexUpload: false,
      matchAltTitles: false,
      replaceBorder: false,
      driveSync: false,
    });
    setBorderType("");
    setCustomHex("");
    setIsReorderMode(false);
    setErrors({});
    setBlurredFields(new Set());
    setConfirmDelete(false);
  };

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch("/api/settings/get-poster-renamerr");
        const result = await response.json();

        if (result.success && result.data) {
          const d = result.data;
          setLogLevel(d.log_level || "info");
          setPosterRoot(d.poster_root || "");
          setAssetDirectory(d.asset_directory || "");
          setSourceFolders(d.source_folders?.length ? d.source_folders : [""]);
          setLibraries(d.libraries?.length ? d.libraries : [""]);
          setSettings({
            assetFolders: d.asset_folders || false,
            cleanAssets: d.clean_assets || false,
            unmatchedAssets: d.unmatched_assets || false,
            replaceBorder: d.replace_border || false,
            webhookRun: d.webhook_run || false,
            unmatchedOnly: d.unmatched_only || false,
            plexUpload: d.plex_upload || false,
            matchAltTitles: d.match_alt_titles || false,
            driveSync: d.drive_sync || false,
          });
          setBorderType(d.border_type || "");
          setCustomHex(d.custom_hex || "");

          if (d.is_configured) {
            setInitialState({
              logLevel: d.log_level || "",
              posterRoot: d.poster_root || "",
              assetDirectory: d.asset_directory || "",
              sourceFolders: d.source_folders?.length ? d.source_folders : [""],
              libraries: d.libraries.length ? d.libraries : [""],
              settings: {
                assetFolders: d.asset_folders || false,
                cleanAssets: d.clean_assets || false,
                unmatchedAssets: d.unmatched_assets || false,
                replaceBorder: d.replace_border || false,
                webhookRun: d.webhook_run || false,
                unmatchedOnly: d.unmatched_only || false,
                plexUpload: d.plex_upload || false,
                matchAltTitles: d.match_alt_titles || false,
                driveSync: d.drive_sync || false,
              },
              borderType: d.border_type || "",
              customHex: d.custom_hex || "",
            });
          }
        }
      } catch (error) {
        console.error("Error fetching settings:", error);
      }
    };
    fetchSettings();
  }, []);

  useEffect(() => {
    if (!fetchLibrariesError) return;
    const handleClick = () => setFetchLibrariesError(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [fetchLibrariesError]);

  useEffect(() => {
    if (!fetchFoldersError) return;
    const handleClick = () => setFetchFoldersError(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [fetchFoldersError]);

  useEffect(() => {
    if (isReorderMode) {
      const initial = {};
      sourceFolders.forEach((_, i) => {
        initial[i] = String(i + 1);
      });
      setReorderValues(initial);
    }
  }, [sourceFolders, isReorderMode]);

  const hasChanges = useMemo(() => {
    if (!initialState) return false;
    const validSourceFolders = sourceFolders.filter((f) => f.trim() !== "");
    const validLibraries = libraries.filter((f) => f.trim() !== "");
    const validInitialSourceFolders = initialState.sourceFolders.filter(
      (f) => f.trim() !== "",
    );
    const validInitialLibraries = initialState.libraries.filter(
      (f) => f.trim() !== "",
    );

    const borderChanged = settings.replaceBorder
      ? borderType !== initialState.borderType ||
        (borderType === "custom" && customHex !== initialState.customHex)
      : initialState.settings.replaceBorder !== settings.replaceBorder;
    return (
      logLevel !== initialState.logLevel ||
      posterRoot !== initialState.posterRoot ||
      assetDirectory !== initialState.assetDirectory ||
      JSON.stringify(settings) !== JSON.stringify(initialState.settings) ||
      JSON.stringify(validSourceFolders) !==
        JSON.stringify(validInitialSourceFolders) ||
      JSON.stringify(validLibraries) !==
        JSON.stringify(validInitialLibraries) ||
      borderChanged
    );
  }, [
    initialState,
    borderType,
    logLevel,
    customHex,
    posterRoot,
    assetDirectory,
    settings,
    sourceFolders,
    libraries,
  ]);

  useEffect(() => {
    onDirtyChange?.(hasChanges);
  }, [hasChanges, onDirtyChange]);
  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-white">Poster Renamerr</h2>
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
        <div className="mt-4 flex flex-col gap-2 border-b border-gray-600 pb-2 md:flex-row">
          <div className="mb-2 flex flex-1 flex-col">
            <h2 className="mb-2 text-sm font-medium text-white">
              Root Directory
              <span className="text-xs font-medium text-red-500"> *</span>
            </h2>
            <div className="relative">
              <input
                type="text"
                value={posterRoot}
                ref={posterRootRef}
                onChange={(e) => {
                  setPosterRoot(e.target.value);
                  if (blurredFields.has("posterRoot") || errors.posterRoot) {
                    if (e.target.value.trim()) {
                      setErrors((prev) => ({
                        ...prev,
                        posterRoot: null,
                      }));
                    } else {
                      setErrors((prev) => ({ ...prev, posterRoot: true }));
                    }
                  }
                }}
                onBlur={() => {
                  setPopupField(null);
                  if (errors.posterRoot) {
                    setBlurredFields((prev) => new Set(prev).add("posterRoot"));
                  }
                }}
                className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("posterRoot") && errors.posterRoot ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                placeholder="/posters"
              />
              {popupField === "posterRoot" && errors.posterRoot && (
                <div className="absolute z-10 w-full">
                  <FieldError message={errors.posterRoot} />
                </div>
              )}
              {blurredFields.has("posterRoot") && errors.posterRoot && (
                <span className="mt-1 text-xs text-red-500">Required</span>
              )}
            </div>
          </div>
          <div className="mb-2 flex flex-1 flex-col">
            <h2 className="mb-2 text-sm font-medium text-white">
              Asset Directory
              <span className="text-xs font-medium text-red-500"> *</span>
            </h2>
            <div className="relative">
              <input
                type="text"
                value={assetDirectory}
                ref={assetDirectoryRef}
                onChange={(e) => {
                  setAssetDirectory(e.target.value);
                  if (
                    blurredFields.has("assetDirector") &&
                    errors.assetDirectory
                  ) {
                    if (e.target.value.trim()) {
                      setErrors((prev) => ({
                        ...prev,
                        assetDirectory: null,
                      }));
                    } else {
                      setErrors((prev) => ({ ...prev, assetDirectory: true }));
                    }
                  }
                }}
                onBlur={() => {
                  setPopupField(null);
                  if (errors.assetDirectory) {
                    setBlurredFields((prev) =>
                      new Set(prev).add("assetDirectory"),
                    );
                  }
                }}
                className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("assetDirectory") && errors.assetDirectory ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                placeholder="/assets"
              />
              {popupField === "assetDirectory" && errors.assetDirectory && (
                <div className="absolute z-10 w-full">
                  <FieldError message={errors.assetDirectory} />
                </div>
              )}
              {blurredFields.has("assetDirectory") && errors.assetDirectory && (
                <span className="mt-1 text-xs text-red-500">Required</span>
              )}
            </div>
          </div>
        </div>
        <div className="gap-2 border-b border-gray-600 py-2">
          <div className="mb-1 flex items-center justify-between">
            <h2 className="text-sm font-medium text-white">
              Source Folders
              <span className="text-xs font-medium text-red-500"> *</span>
            </h2>
            <button
              onClick={() => {
                setIsReorderMode(!isReorderMode);
                if (!isReorderMode) setShowAllFolders(true);
              }}
              disabled={sourceFolders.length === 1}
              className={`mb-1 mt-2 flex items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium transition-colors disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-gray-600 ${isReorderMode ? "bg-blue-600 text-white hover:bg-blue-700" : "bg-gray-500 text-gray-300 hover:bg-gray-600"}`}
            >
              <ArrowUpDown size={14} />
              {isReorderMode ? "Done" : "Reorder"}
            </button>
          </div>
          {isReorderMode && (
            <span className="mb-1 text-xs text-gray-400">
              Priority: Top (highest) {"->"} Bottom (lowest) -- Type a number to
              reposition
            </span>
          )}
          <div className="flex flex-col gap-1">
            {(showAllFolders
              ? sourceFolders
              : sourceFolders.slice(0, FOLDERS_PREVIEW)
            ).map((folder, index) => (
              <div key={index} className="flex items-center gap-2">
                {isReorderMode && (
                  <input
                    type="text"
                    inputMode="numeric"
                    value={reorderValues[index] ?? String(index + 1)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.target.blur();
                      }
                    }}
                    onChange={(e) => {
                      setReorderValues((prev) => ({
                        ...prev,
                        [index]: e.target.value,
                      }));
                    }}
                    onBlur={() => {
                      const newPos = parseInt(reorderValues[index]) - 1;
                      if (
                        isNaN(newPos) ||
                        newPos < 0 ||
                        newPos >= sourceFolders.length
                      ) {
                        setReorderValues((prev) => ({
                          ...prev,
                          [index]: String(index + 1),
                        }));
                        return;
                      }
                      const newFolders = [...sourceFolders];
                      const [moved] = newFolders.splice(index, 1);
                      newFolders.splice(newPos, 0, moved);
                      setSourceFolders(newFolders);
                    }}
                    className="h-10 w-10 flex-shrink-0 rounded-md border-gray-600 bg-gray-600 px-1 text-center text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                )}
                <div className="relative w-full">
                  <input
                    type="text"
                    value={folder}
                    ref={index === 0 ? sourceFoldersRef : null}
                    onChange={(e) => {
                      updateFolder(index, e.target.value);
                      if (
                        blurredFields.has("sourceFolders") ||
                        errors.sourceFolders
                      ) {
                        const updatedSourceFolders = sourceFolders.map(
                          (folder, i) =>
                            i === index ? e.target.value : folder,
                        );
                        const hasAtLeastOne = updatedSourceFolders.some(
                          (folder) => folder.trim(),
                        );
                        if (hasAtLeastOne) {
                          setErrors((prev) => ({
                            ...prev,
                            sourceFolders: null,
                          }));
                        } else {
                          setErrors((prev) => ({
                            ...prev,
                            sourceFolders: true,
                          }));
                        }
                      }
                    }}
                    onBlur={() => {
                      setPopupField(null);
                      if (errors.sourceFolders) {
                        setBlurredFields((prev) =>
                          new Set(prev).add("sourceFolders"),
                        );
                      }
                    }}
                    className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${!isReorderMode && blurredFields.has("sourceFolders") && errors.sourceFolders ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                    disabled={isReorderMode}
                    placeholder="cl2k-dweagle79"
                  />
                  {index === 0 &&
                    popupField === "sourceFolders" &&
                    errors.sourceFolders && (
                      <div className="absolute z-10 w-full">
                        <FieldError message={errors.sourceFolders} />
                      </div>
                    )}
                </div>
                {isReorderMode ? (
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => moveUp(index)}
                      disabled={index === 0}
                      className="rounded bg-gray-700 p-1 text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-30"
                      title="Move up (higher priority)"
                    >
                      <ChevronUp size={16} />
                    </button>
                    <button
                      onClick={() => moveDown(index)}
                      disabled={index === sourceFolders.length - 1}
                      className="rounded bg-gray-700 p-1 text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-30"
                      title="Move down (lower priority)"
                    >
                      <ChevronDown size={16} />
                    </button>
                  </div>
                ) : (
                  sourceFolders.length > 1 && (
                    <button
                      onClick={() => removeFolder(index)}
                      className="rounded-md bg-gray-700 px-3 py-2 text-white transition-colors hover:bg-gray-600"
                    >
                      <X size={16} />
                    </button>
                  )
                )}
              </div>
            ))}
            {!isReorderMode && sourceFolders.length > FOLDERS_PREVIEW && (
              <button
                onClick={() => setShowAllFolders(!showAllFolders)}
                className="mt-1 text-xs font-medium text-blue-400 transition-colors hover:text-blue-300"
              >
                {showAllFolders
                  ? "Show less"
                  : `Show ${sourceFolders.length - FOLDERS_PREVIEW} more`}
              </button>
            )}
            {!isReorderMode &&
              blurredFields.has("sourceFolders") &&
              errors.sourceFolders && (
                <span className="text-xs text-red-500">Required</span>
              )}
            {!isReorderMode && (
              <div className="flex flex-col gap-2 pb-1">
                <span className="mt-1 text-xs text-gray-400">
                  Enter a source folder name (eg., cl2k-dweagle79,
                  cl2k/dweagle79) -- Source folder names must include "mm2k" or
                  "cl2k" for folder filters to work when loading folders
                </span>
                <div className="mb-1 flex flex-col gap-2 sm:flex-row">
                  <button
                    onClick={addFolder}
                    className="mt-1 flex w-full items-center justify-center gap-2 self-start rounded-md bg-blue-600 px-3 py-2 text-xs text-white transition-colors hover:bg-blue-700 sm:w-auto"
                  >
                    <Plus size={15} />
                    Add Folder
                  </button>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                    <div className="relative">
                      <button
                        className="mt-1 flex w-full items-center justify-center gap-2 self-start rounded-md bg-gray-500 px-3 py-2 text-xs text-white transition-colors hover:bg-gray-600 sm:w-auto"
                        onClick={handleFetchFolders}
                      >
                        <Plus size={15} />
                        Load Folders
                      </button>
                      {fetchFoldersError && (
                        <div className="absolute z-10 w-full">
                          <FieldError message={fetchFoldersError} />
                        </div>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-3">
                      <label className="flex cursor-pointer items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={folderFilters.mm2k}
                          onChange={(e) =>
                            setFolderFilters((prev) => ({
                              ...prev,
                              mm2k: e.target.checked,
                              cl2k: e.target.checked ? false : prev.cl2k,
                            }))
                          }
                          className="h-3 w-3 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <span className="text-xs text-gray-400">mm2k</span>
                      </label>

                      <label className="flex cursor-pointer items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={folderFilters.cl2k}
                          onChange={(e) =>
                            setFolderFilters((prev) => ({
                              ...prev,
                              cl2k: e.target.checked,
                              mm2k: e.target.checked ? false : prev.mm2k,
                            }))
                          }
                          className="h-3 w-3 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <span className="text-xs text-gray-400">cl2k</span>
                      </label>

                      <label className="flex cursor-pointer items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={!folderFilters.mm2k && !folderFilters.cl2k}
                          onChange={() =>
                            setFolderFilters({ mm2k: false, cl2k: false })
                          }
                          className="h-3 w-3 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <span className="text-xs text-gray-400">all</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2 border-b border-gray-600 py-4">
          <h2 className="text-sm font-medium text-white">
            Library Names
            <span className="text-xs font-medium text-red-500"> *</span>
          </h2>
          <div className="flex flex-col gap-1">
            {libraries.map((library, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="relative w-full">
                  <input
                    value={library}
                    ref={index === 0 ? librariesRef : null}
                    onChange={(e) => {
                      updateLibrary(index, e.target.value);
                      if (blurredFields.has("libraries") || errors.libraries) {
                        const updatedLibraries = libraries.map((lib, i) =>
                          i === index ? e.target.value : lib,
                        );
                        const hasAtLeastOne = updatedLibraries.some((lib) =>
                          lib.trim(),
                        );
                        if (hasAtLeastOne) {
                          setErrors((prev) => ({
                            ...prev,
                            libraries: null,
                          }));
                        } else {
                          setErrors((prev) => ({ ...prev, libraries: true }));
                        }
                      }
                    }}
                    onBlur={() => {
                      setPopupField(null);
                      if (errors.libraries) {
                        setBlurredFields((prev) =>
                          new Set(prev).add("libraries"),
                        );
                      }
                    }}
                    type="text"
                    className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("libraries") && errors.libraries ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                    placeholder="Movies"
                  />
                  {index === 0 &&
                    popupField === "libraries" &&
                    errors.libraries && (
                      <div className="absolute z-10 w-full">
                        <FieldError message={errors.libraries} />
                      </div>
                    )}
                </div>
                {libraries.length > 1 && (
                  <button
                    onClick={() => removeLibrary(index)}
                    className="rounded-md bg-gray-700 px-3 py-2 text-white transition-colors hover:bg-gray-500"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            ))}
            {blurredFields.has("libraries") && errors.libraries && (
              <span className="text-xs text-red-500">Required</span>
            )}
          </div>
          <div className="flex flex-col gap-2 pb-1">
            <span className="text-xs text-gray-400">
              Enter Plex library name -- This must match exactly what is in Plex
              (eg., Movies, Movies 4k, TV Shows)
            </span>
            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                className="mt-1 flex w-full items-center justify-center gap-2 self-start rounded-md bg-blue-600 px-3 py-2 text-xs text-white transition-colors hover:bg-blue-700 sm:w-auto"
                onClick={addLibrary}
              >
                <Plus size={15} />
                Add Library
              </button>
              <div className="relative">
                <button
                  className="mt-1 flex w-full items-center justify-center gap-2 self-start rounded-md bg-gray-500 px-3 py-2 text-xs text-white transition-colors hover:bg-gray-600 sm:w-auto"
                  onClick={handleFetchLibraries}
                >
                  <Plus size={15} />
                  Load Libraries
                </button>
                {fetchLibrariesError && (
                  <div className="absolute z-10 w-full">
                    <FieldError message={fetchLibrariesError} />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="mb-2 grid grid-cols-1 gap-4 border-b border-gray-600 py-5 md:grid-cols-2 lg:grid-cols-3">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.assetFolders}
              onChange={(e) =>
                setSettings({ ...settings, assetFolders: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Asset Folders</span>
              <span className="text-xs text-gray-400">
                Enable asset folder configuration for posters
              </span>
            </div>
          </label>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.cleanAssets}
              onChange={(e) =>
                setSettings({ ...settings, cleanAssets: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Clean Assets</span>
              <span className="text-xs text-gray-400">
                Remove orphaned poster files upon run completion
              </span>
            </div>
          </label>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.unmatchedAssets}
              onChange={(e) =>
                setSettings({ ...settings, unmatchedAssets: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Unmatched Assets</span>
              <span className="text-xs text-gray-400">
                Run unmatched assets upon run completion
              </span>
            </div>
          </label>

          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.webhookRun}
              onChange={(e) =>
                setSettings({ ...settings, webhookRun: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-sm text-white">Webhook Run</span>
                <div className="relative flex items-center">
                  <Info
                    size={14}
                    className="text-gray-400 hover:text-white"
                    onMouseEnter={() => showToolTip("webhookRun")}
                    onMouseLeave={hideTooltip}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveTooltip(
                        activeTooltip === "webhookRun" ? null : "webhookRun",
                      );
                    }}
                  />
                  {activeTooltip === "webhookRun" && (
                    <div
                      className="absolute left-full top-1/2 z-10 ml-2 mt-1 w-60 -translate-y-1/2 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-gray-300 shadow-lg sm:w-96"
                      onMouseEnter={cancelHide}
                      onMouseLeave={hideTooltip}
                    >
                      <span className="text-xs text-gray-300">
                        Please read the webhook configuration guide here.
                        <br />
                        <br />
                      </span>
                      <a
                        className="break-all text-blue-400"
                        href="https://github.com/zarskie/daps-ui/wiki/Webhook-Run"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        https://github.com/zarskie/daps-ui/wiki/Webhook-Run
                      </a>
                    </div>
                  )}
                </div>
              </div>
              <span className="text-xs text-gray-400">
                Enable webhook-triggered poster processing
              </span>
            </div>
          </label>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.unmatchedOnly}
              onChange={(e) =>
                setSettings({ ...settings, unmatchedOnly: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Unmatched Only</span>
              <span className="text-xs text-gray-400">
                Enable running renamerr on only unmatched assets
              </span>
            </div>
          </label>

          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.plexUpload}
              onChange={(e) =>
                setSettings({ ...settings, plexUpload: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Plex Upload</span>
              <span className="text-xs text-gray-400">
                Run plex uploaderr upon run completion
              </span>
            </div>
          </label>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.matchAltTitles}
              onChange={(e) =>
                setSettings({ ...settings, matchAltTitles: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Match Alt Titles</span>
              <span className="text-xs text-gray-400">
                Enable matching of alternate titles
              </span>
            </div>
          </label>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.replaceBorder}
              onChange={(e) =>
                setSettings({ ...settings, replaceBorder: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Replace Border</span>
              <span className="text-xs text-gray-400">
                Enable replacing borders on poster files
              </span>
            </div>
          </label>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={settings.driveSync}
              onChange={(e) =>
                setSettings({ ...settings, driveSync: e.target.checked })
              }
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
            />
            <div className="flex flex-col">
              <span className="text-sm text-white">Drive Sync</span>
              <span className="text-xs text-gray-400">
                Run drive sync before renamerr run
              </span>
            </div>
          </label>
        </div>
        {settings.replaceBorder && (
          <div className="flex w-full flex-col items-start justify-between gap-2 border-b border-gray-600 py-2 md:flex-row md:items-start">
            <div className="flex w-full flex-col">
              <h2 className="mb-2 text-sm font-medium text-white">
                Border Type
                <span className="text-xs font-medium text-red-500"> *</span>
              </h2>
              <div className="relative w-full">
                <select
                  value={borderType}
                  ref={borderTypeRef}
                  onChange={(e) => {
                    setBorderType(e.target.value);
                    if (blurredFields.has("borderType") || errors.borderType) {
                      if (e.target.value.trim()) {
                        setErrors((prev) => ({
                          ...prev,
                          borderType: null,
                        }));
                      } else {
                        setErrors((prev) => ({ ...prev, borderType: true }));
                      }
                    }
                  }}
                  onBlur={() => {
                    setPopupField(null);
                    if (errors.borderType) {
                      setBlurredFields((prev) =>
                        new Set(prev).add("borderType"),
                      );
                    }
                  }}
                  className={`w-full appearance-none rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("borderType") && errors.borderType ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                >
                  <option value="">Select border type</option>
                  <option value="remove">Remove</option>
                  <option value="black">Black</option>
                  <option value="custom">Custom</option>
                </select>
                <ChevronDown
                  size={18}
                  className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                />
                {popupField === "borderType" && errors.borderType && (
                  <div className="absolute z-10 w-full">
                    <FieldError message={errors.borderType} />
                  </div>
                )}
              </div>
              <div className="min-h-[1rem]">
                {blurredFields.has("borderType") && errors.borderType && (
                  <span className="text-xs text-red-500">Required</span>
                )}
              </div>
            </div>
            {borderType === "custom" && (
              <div className="flex w-full flex-col">
                <h2 className="mb-2 text-sm font-medium text-white">
                  Hex Code
                  <span className="text-xs font-medium text-red-500"> *</span>
                </h2>
                <div className="relative">
                  <input
                    type="text"
                    ref={customHexRef}
                    value={customHex}
                    onChange={(e) => {
                      setCustomHex(e.target.value);
                      if (blurredFields.has("customHex") || errors.customHex) {
                        if (e.target.value.trim()) {
                          setErrors((prev) => ({
                            ...prev,
                            customHex: null,
                          }));
                        } else {
                          setErrors((prev) => ({
                            ...prev,
                            customHex: true,
                          }));
                        }
                      }
                    }}
                    onBlur={() => {
                      setPopupField(null);
                      if (errors.customHex) {
                        setBlurredFields((prev) =>
                          new Set(prev).add("customHex"),
                        );
                      }
                    }}
                    className={`w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("customHex") && errors.customHex ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                    placeholder="#000000"
                  />
                  {popupField === "customHex" && errors.customHex && (
                    <div className="absolute z-10 w-full">
                      <FieldError message={errors.customHex} />
                    </div>
                  )}
                </div>
                <div className="min-h-[1rem]">
                  {blurredFields.has("customHex") && errors.customHex && (
                    <span className="text-xs text-red-500">Required</span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
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
          <div className="relative w-full sm:w-auto">
            {confirmDelete ? (
              <div className="flex w-full items-center gap-2 sm:w-auto">
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="flex flex-1 items-center justify-center rounded-md bg-gray-800 px-4 py-2 text-red-500 transition-colors hover:bg-gray-900 hover:text-red-400 sm:flex-none"
                >
                  <X size={16} />
                </button>
                <button
                  onClick={resetForm}
                  disabled={isLoading}
                  className="flex flex-1 items-center justify-center rounded-md bg-gray-800 px-4 py-2 text-green-400 transition-colors hover:bg-gray-900 hover:text-green-300 disabled:opacity-50 sm:flex-none"
                >
                  <Check size={16} />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(true)}
                disabled={isLoading}
                className="flex w-full items-center justify-center rounded-md bg-gray-500 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
              >
                {isLoading ? "Clearing..." : "Clear"}
              </button>
            )}
            {confirmDelete && (
              <div className="absolute bottom-full left-0 mb-2 whitespace-nowrap rounded-md border border-gray-800 bg-gray-950 px-3 py-1.5">
                <span className="text-xs text-gray-400">Are you sure?</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default PosterRenamerrSettings;
