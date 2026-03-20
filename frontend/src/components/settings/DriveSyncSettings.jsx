import {
  ChevronDown,
  X,
  Eye,
  EyeOff,
  Plus,
  ChevronUp,
  Check,
  Info,
} from "lucide-react";
import { useEffect, useMemo, useState, useRef } from "react";
import FieldError from "../common/FieldError";

const DriveSyncSettings = ({ onDirtyChange }) => {
  const clientIdRef = useRef(null);
  const clientSecretRef = useRef(null);
  const oAuthTokenRef = useRef(null);
  const serviceAccountRef = useRef(null);
  const rootDirectoryRef = useRef(null);
  const driveNameRef = useRef(null);
  const driveIdRef = useRef(null);
  const tooltipTimeout = useRef(null);
  const [logLevel, setLogLevel] = useState("info");
  const [rootDirectory, setRootDirectory] = useState("");
  const [driveName, setDriveName] = useState("");
  const [driveId, setDriveId] = useState("");
  const [driveType, setDriveType] = useState("");
  const [friendlyName, setFriendlyName] = useState("");
  const [addingDrive, setAddingDrive] = useState(null);
  const [gdrives, setGdrives] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [initialState, setInitialState] = useState(null);
  const [authInitialState, setAuthInitialState] = useState(null);
  const [driveInitialState, setDriveInitialState] = useState(null);
  const [editingDrive, setEditingDrive] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [errors, setErrors] = useState({});
  const [blurredFields, setBlurredFields] = useState(new Set());
  const [popupField, setPopupField] = useState(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [oAuthToken, setOauthToken] = useState("");
  const [serviceAccount, setServiceAccount] = useState("");
  const [authMethod, setAuthMethod] = useState("");
  const [showClientSecret, setShowClientSecret] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [rcloneConfigured, setRcloneConfigured] = useState(false);
  const [drivePresets, setDrivePresets] = useState([]);
  const [drivePreset, setDrivePreset] = useState("");
  const [expandedDrives, setExpandedDrives] = useState(new Set());
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showAllDrives, setShowAllDrives] = useState(false);
  const [activeTooltip, setActiveTooltip] = useState(null);

  const availablePresets = drivePresets.filter(
    (preset) => !gdrives.some((g) => g.drive_id === preset.drive_id),
  );
  const DRIVES_PREVIEW = 5;
  const tokenPlaceholder = `{
    "access_token":"ya29.a0AfH6SMB...",
    "token_type":"Bearer",
    "refresh_token":"1//0gLd...",
    "expiry":"2024-01-15T10:30:00Z"
  }`;

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

  const handleSaveAuth = async () => {
    const newErrors = {};
    if (authMethod === "oAuth") {
      if (!clientId) newErrors.clientId = true;
      if (!clientSecret) newErrors.clientSecret = true;
      if (!oAuthToken) newErrors.oAuthToken = true;
    }

    if (authMethod === "serviceAccount") {
      if (!serviceAccount) newErrors.serviceAccount = true;
    }
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      if (newErrors.clientId) {
        setPopupField("clientId");
        clientIdRef.current?.focus();
      } else if (newErrors.clientSecret) {
        setPopupField("clientSecret");
        clientSecretRef.current?.focus();
      } else if (newErrors.oAuthToken) {
        setPopupField("oAuthToken");
        oAuthTokenRef.current?.focus();
      } else if (newErrors.serviceAccount) {
        setPopupField("serviceAccount");
        serviceAccountRef.current?.focus();
      }
      return;
    }

    setErrors({});
    setIsLoading(true);
    try {
      const payload = {
        authMethod: authMethod.trim(),
        clientId: authMethod === "oAuth" ? clientId.trim() : "",
        clientSecret: authMethod === "oAuth" ? clientSecret.trim() : "",
        oAuthToken: authMethod === "oAuth" ? oAuthToken.trim() : "",
        serviceAccount:
          authMethod === "serviceAccount" ? serviceAccount.trim() : "",
      };
      const response = await fetch("/api/settings/save-rclone-config", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (response.ok) {
        setIsSidebarOpen(false);
        setErrors({});
        setBlurredFields(new Set());
        setShowToken(false);
        setShowClientSecret(false);
        setRcloneConfigured(true);
        setAuthInitialState({
          authMethod: authMethod.trim(),
          clientId: clientId.trim(),
          clientSecret: clientSecret.trim(),
          oAuthToken: oAuthToken.trim(),
          serviceAccount: serviceAccount.trim(),
        });
      } else {
        alert(`Failed!: ${result.message}`);
      }
    } catch (error) {
      console.error("Error saving settings:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveDrive = async () => {
    const newErrors = {};
    if (!driveName) newErrors.driveName = true;
    if (!driveId) newErrors.driveId = true;

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      if (newErrors.driveName) {
        setPopupField("driveName");
        driveNameRef.current?.focus();
      } else if (newErrors.driveId) {
        setPopupField("driveId");
        driveIdRef.current?.focus();
      }
      return;
    }

    setErrors({});
    setIsLoading(true);
    try {
      const payload = {
        ...(editingDrive && { id: editingDrive.id }),
        driveType: driveType.trim(),
        driveName: driveName.trim(),
        driveId: driveId.trim(),
        friendlyName: friendlyName.trim(),
      };
      const response = await fetch(
        editingDrive ? "/api/settings/update-drive" : "/api/settings/add-drive",
        {
          method: editingDrive ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        },
      );
      const result = await response.json();
      if (response.ok) {
        setIsSidebarOpen(false);
        setAddingDrive(null);
        setEditingDrive(null);
        setDrivePreset("");
        setDriveType("");
        setDriveName("");
        setDriveId("");
        setFriendlyName("");
        setErrors({});
        setBlurredFields(new Set());
        const drivesResponse = await fetch("/api/settings/get-drives");
        const drivesResult = await drivesResponse.json();
        if (drivesResult.success) {
          const sorted = [...drivesResult.drives].sort((a, b) => {
            if (a.drive_type !== b.drive_type)
              return a.drive_type.localeCompare(b.drive_type);
            return a.friendly_name.localeCompare(b.friendly_name);
          });
          setGdrives(sorted);
        }
      } else {
        alert(`Failed!: ${result.message}`);
      }
    } catch (error) {
      console.error("Error saving settings:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditDrive = (drive) => {
    setEditingDrive(drive);
    setDrivePreset("");
    setFriendlyName(drive.friendly_name || "");
    setDriveType(drive.drive_type || "");
    setDriveName(drive.drive_name || "");
    setDriveId(drive.drive_id || "");
    setDriveInitialState({
      friendlyName: drive.friendly_name || "",
      driveType: drive.drive_type || "",
      driveName: drive.drive_name || "",
      driveId: drive.drive_id || "",
    });
    setErrors({});
    setBlurredFields(new Set());
    setAddingDrive(true);
    setIsSidebarOpen(true);
  };
  const handleDeleteDrive = async () => {
    if (!editingDrive) return;
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch("/api/settings/delete-drive", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: editingDrive.id }),
      });
      const result = await response.json();
      if (response.ok) {
        setIsSidebarOpen(false);
        setEditingDrive(null);
        setDriveName("");
        setDriveId("");
        setDriveType("");
        setFriendlyName("");
        setDriveInitialState(null);
        setErrors({});
        setBlurredFields(new Set());
        setConfirmDelete(false);
        const drivesResponse = await fetch("/api/settings/get-drives");
        const drivesResult = await drivesResponse.json();
        if (drivesResult.success) {
          const sorted = [...drivesResult.drives].sort((a, b) => {
            if (a.drive_type !== b.drive_type)
              return a.drive_type.localeCompare(b.drive_type);
            return a.friendly_name.localeCompare(b.friendly_name);
          });
          setGdrives(sorted);
        }
      } else {
        alert(`Failed!: ${result.message}`);
      }
    } catch (error) {
      console.error("Error deleting drive:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveForm = async () => {
    const newErrors = {};
    if (!rootDirectory) newErrors.rootDirectory = true;
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      if (newErrors.rootDirectory) {
        setPopupField("rootDirectory");
        rootDirectoryRef.current?.focus();
      }
      return;
    }

    setErrors({});
    setIsLoading(true);
    try {
      const payload = {
        logLevel: logLevel.trim(),
        rootDirectory: rootDirectory.trim(),
      };
      const response = await fetch("/api/settings/save-drive-sync", {
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
          rootDirectory: rootDirectory.trim(),
        });
      } else {
        alert(`Failed!: ${result.message}`);
      }
    } catch (error) {
      console.error("Error saving settings:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setIsSidebarOpen(false);
    setAddingDrive(null);
    setEditingDrive(null);
    setDrivePreset("");
    setDriveType("");
    setFriendlyName("");
    setDriveName("");
    setDriveId("");
    setDriveInitialState(null);
    setAuthMethod(authInitialState?.authMethod || "");
    setClientId(authInitialState?.clientId || "");
    setClientSecret(authInitialState?.clientSecret || "");
    setOauthToken(authInitialState?.oAuthToken || "");
    setServiceAccount(authInitialState?.serviceAccount || "");
    setErrors({});
    setBlurredFields(new Set());
    setShowClientSecret(false);
    setShowToken(false);
    setConfirmDelete(false);
  };

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch("/api/settings/get-drive-sync");
        const result = await response.json();
        if (result.success && result.data) {
          const d = result.data;
          setLogLevel(d.log_level || "info");
          setRootDirectory(d.root_directory || "");
          if (d.is_configured) {
            setInitialState({
              logLevel: d.log_level || "info",
              rootDirectory: d.root_directory || "",
            });
          }
          if (d.auth_method) {
            setAuthMethod(d.auth_method || "");
            setClientId(d.client_id || "");
            setClientSecret(d.client_secret || "");
            setOauthToken(d.oauth_token || "");
            setServiceAccount(d.service_account || "");
            setShowToken(!d.oauth_token);
            setRcloneConfigured(true);
            setAuthInitialState({
              authMethod: d.auth_method || "",
              clientId: d.client_id || "",
              clientSecret: d.client_secret || "",
              oAuthToken: d.oauth_token || "",
              serviceAccount: d.service_account || "",
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
    const fetchDrives = async () => {
      try {
        const response = await fetch("/api/settings/get-drives");
        const result = await response.json();
        if (result.success) {
          const sorted = [...result.drives].sort((a, b) => {
            if (a.drive_type !== b.drive_type)
              return a.drive_type.localeCompare(b.drive_type);
            return a.friendly_name.localeCompare(b.friendly_name);
          });
          setGdrives(sorted);
        }
      } catch (error) {
        console.error("Error fetching drives:", error);
      }
    };
    fetchDrives();
  }, []);

  useEffect(() => {
    if (!addingDrive) return;
    const fetchPresets = async () => {
      try {
        const response = await fetch("/api/settings/get-drive-presets");
        const result = await response.json();
        console.log("preset result:", result);
        if (result.success) {
          const sorted = [...result.presets].sort((a, b) => {
            if (a.type !== b.type) return a.type.localeCompare(b.type);
            return a.name.localeCompare(b.name);
          });
          setDrivePresets(sorted);
        }
      } catch (error) {
        console.error("Error fetching drive presets:", error);
      }
    };
    fetchPresets();
  }, [addingDrive]);

  const sidebarHasChanges = useMemo(() => {
    if (!authInitialState) return false;
    return (
      authMethod !== authInitialState.authMethod ||
      clientId !== authInitialState.clientId ||
      clientSecret !== authInitialState.clientSecret ||
      oAuthToken !== authInitialState.oAuthToken ||
      serviceAccount !== authInitialState.serviceAccount
    );
  }, [
    authInitialState,
    authMethod,
    clientId,
    clientSecret,
    oAuthToken,
    serviceAccount,
  ]);

  const driveHasChanges = useMemo(() => {
    if (!driveInitialState) return false;
    return (
      driveType !== driveInitialState.driveType ||
      friendlyName !== driveInitialState.friendlyName ||
      driveName !== driveInitialState.driveName ||
      driveId !== driveInitialState.driveId
    );
  }, [driveInitialState, driveType, friendlyName, driveName, driveId]);

  const hasChanges = useMemo(() => {
    if (!initialState) return false;
    return (
      logLevel !== initialState.logLevel ||
      rootDirectory !== initialState.rootDirectory
    );
  }, [initialState, logLevel, rootDirectory]);

  useEffect(() => {
    onDirtyChange?.(hasChanges);
  }, [hasChanges, onDirtyChange]);

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-white">Drive Sync</h2>
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
        <div className="mb-2 flex flex-1 flex-col border-b border-gray-600 pb-4">
          <h2 className="mb-2 mt-1 text-sm font-medium text-white">
            Root Directory
            <span className="text-xs font-medium text-red-500"> *</span>
          </h2>
          <div className="relative">
            <input
              type="text"
              value={rootDirectory}
              ref={rootDirectoryRef}
              onChange={(e) => {
                setRootDirectory(e.target.value);
                if (
                  blurredFields.has("rootDirectory") ||
                  errors.rootDirectory
                ) {
                  if (e.target.value.trim()) {
                    setErrors((prev) => ({
                      ...prev,
                      rootDirectory: null,
                    }));
                  } else {
                    setErrors((prev) => ({ ...prev, rootDirectory: true }));
                  }
                }
              }}
              onBlur={() => {
                setPopupField(null);
                if (errors.rootDirectory) {
                  setBlurredFields((prev) =>
                    new Set(prev).add("rootDirectory"),
                  );
                }
              }}
              className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("rootDirectory") && errors.rootDirectory ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
              placeholder="/posters"
            />
            {popupField === "rootDirectory" && errors.rootDirectory && (
              <div className="absolute z-10 w-full">
                <FieldError message={errors.rootDirectory} />
              </div>
            )}
            {blurredFields.has("rootDirectory") && errors.rootDirectory && (
              <span className="mt-1 text-xs text-red-500">Required</span>
            )}
          </div>
        </div>
        <div className="mb-2 flex flex-col border-b border-gray-600 pb-4">
          <h2 className="mb-2 mt-1 text-sm font-medium text-white">G-Drives</h2>
          {gdrives.length === 0 ? (
            <span className="mb-4 text-sm text-gray-400">
              No G-Drives configured yet.
            </span>
          ) : (
            <div className="mb-4 flex flex-col gap-4 rounded-md border border-gray-600 bg-gray-800 p-4">
              <div className="flex flex-row items-center justify-between gap-3 border-b border-gray-700 pb-2">
                <span className="text-xs font-medium uppercase text-gray-400">
                  Name
                </span>
                <div className="flex shrink-0 items-center gap-10 sm:gap-20">
                  <span className="flex w-16 items-center justify-center text-xs font-medium uppercase text-gray-400">
                    Type
                  </span>
                  <span className="w-[60px]"></span>
                </div>
              </div>
              {(showAllDrives ? gdrives : gdrives.slice(0, DRIVES_PREVIEW)).map(
                (gdrive) => (
                  <div
                    key={`${gdrive.id}`}
                    className={`mt-1 flex flex-row justify-between gap-3 ${expandedDrives.has(gdrive.drive_location) ? "items-start" : "items-center"}`}
                  >
                    <div className="min-w-0 flex-1">
                      <button
                        onClick={() =>
                          setExpandedDrives((prev) => {
                            const next = new Set(prev);
                            next.has(gdrive.drive_location)
                              ? next.delete(gdrive.drive_location)
                              : next.add(gdrive.drive_location);
                            return next;
                          })
                        }
                        className="flex items-center gap-2 text-left"
                      >
                        <span className="text-sm font-medium text-white">
                          {gdrive.friendly_name}
                        </span>
                        {expandedDrives.has(gdrive.drive_location) ? (
                          <ChevronUp
                            size={16}
                            className="shrink-0 text-gray-400"
                          />
                        ) : (
                          <ChevronDown
                            size={16}
                            className="shrink-0 text-gray-400"
                          />
                        )}
                      </button>
                      {expandedDrives.has(gdrive.drive_location) && (
                        <span className="break-all text-sm text-gray-400">
                          {gdrive.drive_location}
                        </span>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-10 sm:gap-20">
                      <span className="flex w-14 shrink-0 items-center justify-center rounded-md bg-gray-600 px-2 py-1 text-xs uppercase text-gray-300">
                        {gdrive.drive_type}
                      </span>
                      <button
                        onClick={() => handleEditDrive(gdrive)}
                        className="w-auto shrink-0 items-start rounded-md px-3 py-1.5 text-sm text-white transition-colors hover:text-blue-500"
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                ),
              )}
              {gdrives.length > DRIVES_PREVIEW && (
                <button
                  onClick={() => setShowAllDrives(!showAllDrives)}
                  className="text-xs text-gray-400 transition-colors hover:text-white"
                >
                  {showAllDrives
                    ? "Show less"
                    : `Show ${gdrives.length - DRIVES_PREVIEW} more`}
                </button>
              )}
            </div>
          )}
          <button
            className="flex w-full items-center justify-center gap-2 self-start rounded-md bg-blue-600 px-4 py-2 text-xs text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            onClick={() => {
              if (!initialState) {
                setErrors((prev) => ({
                  ...prev,
                  rootDirectory:
                    "Please fill out this field and save before adding a G-Drive",
                }));
                setPopupField("rootDirectory");
                rootDirectoryRef.current?.focus();
                return;
              }
              setAddingDrive(true);
              setIsSidebarOpen(true);
              setErrors({});
              setBlurredFields(new Set());
            }}
          >
            <Plus size={16} />
            Add G-Drive
          </button>
        </div>
        {/* Sliding Sidebar */}
        <div
          className={`fixed right-0 top-0 z-[60] h-full w-full transform bg-gray-900 shadow-2xl transition-transform duration-300 ease-in-out sm:max-w-xl ${
            isSidebarOpen ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <div className="flex items-start justify-between bg-gray-700 p-6">
            <div className="flex flex-col gap-2">
              <h3 className="text-xl font-semibold text-white">
                {editingDrive
                  ? "Edit G-Drive"
                  : addingDrive
                    ? "Add G-Drive"
                    : "Auth Configuration"}
              </h3>
              <p className="text-sm text-white">
                {editingDrive
                  ? "Edit G-Drive."
                  : addingDrive
                    ? "Add G-Drive."
                    : "Configure Settings."}
              </p>
            </div>
            <button
              onClick={handleCancel}
              className="rounded-md p-1 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
            >
              <X size={24} />
            </button>
          </div>
          {editingDrive || addingDrive ? (
            <>
              {!editingDrive && (
                <div className="border-b border-gray-700 p-4 md:p-6">
                  <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <label className="text-sm text-white sm:pt-2">
                      Select Preset
                    </label>
                    <div className="flex flex-col">
                      <div className="relative sm:w-80">
                        <select
                          value={drivePreset}
                          onChange={(e) => {
                            setDrivePreset(e.target.value);
                            const selected = drivePresets.find(
                              (p) => p.name === e.target.value,
                            );
                            if (selected) {
                              setDriveType(selected.type);
                              setFriendlyName(selected.friendly_name);
                              setDriveName(selected.name.toLowerCase());
                              setDriveId(selected.drive_id);
                            } else {
                              setDriveType("");
                              setFriendlyName("");
                              setDriveName("");
                              setDriveId("");
                            }
                            setErrors({});
                            setBlurredFields(new Set());
                          }}
                          className="w-full cursor-pointer appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                          onBlur={() => setPopupField(null)}
                        >
                          <option value="">Select Preset</option>
                          <option value="custom">Custom</option>
                          {availablePresets.map((preset) => (
                            <option key={preset.name} value={preset.name}>
                              {preset.name}
                            </option>
                          ))}
                        </select>
                        <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                          <ChevronDown size={18} />
                        </div>
                      </div>
                      {drivePreset && drivePreset !== "custom" && (
                        <p className="mt-2 text-xs text-gray-400">
                          {drivePresets
                            .find((p) => p.name === drivePreset)
                            ?.content.join(", ")}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              {(drivePreset || editingDrive) && (
                <>
                  <div className="p-4 md:p-6">
                    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <label className="text-sm text-white sm:pt-2">
                        Select Type
                      </label>
                      <div className="flex flex-col">
                        <div className="relative sm:w-80">
                          <select
                            value={driveType}
                            onChange={(e) => {
                              setDriveType(e.target.value);
                              setDrivePreset("custom");
                            }}
                            className="w-full cursor-pointer appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <option value="">Select Type</option>
                            <option value="cl2k">cl2k</option>
                            <option value="mm2k">mm2k</option>
                            <option value="other">Other</option>
                          </select>
                          <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                            <ChevronDown size={18} />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 md:p-6">
                    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <label className="text-sm text-white sm:pt-2">
                        Friendly Name
                      </label>
                      <div className="flex flex-col gap-1 sm:w-80">
                        <div className="relative">
                          <input
                            className="w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            type="text"
                            value={friendlyName}
                            onChange={(e) => {
                              setFriendlyName(e.target.value);
                            }}
                            placeholder="Dweagle79"
                          />
                        </div>
                        <span className="mt-1 text-xs text-gray-400">
                          The name displayed in the UI -- if not set will
                          default to drive name
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 md:p-6">
                    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <label className="text-sm text-white sm:pt-2">
                        Drive Name
                        <span className="text-red-500"> *</span>
                      </label>
                      <div className="flex flex-col gap-1 sm:w-80">
                        <div className="relative">
                          <input
                            className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("driveName") && errors.driveName ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                            type="text"
                            value={driveName}
                            ref={driveNameRef}
                            onChange={(e) => {
                              setDriveName(e.target.value);
                              if (
                                blurredFields.has("driveName") ||
                                errors.driveName
                              ) {
                                if (e.target.value.trim()) {
                                  setErrors((prev) => ({
                                    ...prev,
                                    driveName: null,
                                  }));
                                } else {
                                  setErrors((prev) => ({
                                    ...prev,
                                    driveName: true,
                                  }));
                                }
                              }
                            }}
                            onBlur={() => {
                              setPopupField(null);
                              if (errors.driveName) {
                                setBlurredFields((prev) =>
                                  new Set(prev).add("driveName"),
                                );
                              }
                            }}
                            placeholder="cl2k-dweagle79"
                          />
                          {popupField === "driveName" && errors.driveName && (
                            <div className="absolute z-10 w-full">
                              <FieldError message={errors.driveName} />
                            </div>
                          )}
                          {blurredFields.has("driveName") &&
                            errors.driveName && (
                              <span className="mt-1 text-xs text-red-500">
                                Required
                              </span>
                            )}
                        </div>
                        <span className="mt-1 text-xs text-gray-400">
                          The name of the folder in the root directory
                          <br />
                          (eg., cl2k-dweagle79, cl2k/dweagle79)
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 md:p-6">
                    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <label className="text-sm text-white sm:pt-2">
                        Drive Id
                        <span className="text-red-500"> *</span>
                      </label>
                      <div className="flex flex-col gap-1 sm:w-80">
                        <div className="relative">
                          <input
                            className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("driveId") && errors.driveId ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                            type="text"
                            value={driveId}
                            ref={driveIdRef}
                            onChange={(e) => {
                              setDriveId(e.target.value);
                              setDrivePreset("custom");
                              if (
                                blurredFields.has("driveId") ||
                                errors.driveId
                              ) {
                                if (e.target.value.trim()) {
                                  setErrors((prev) => ({
                                    ...prev,
                                    driveId: null,
                                  }));
                                } else {
                                  setErrors((prev) => ({
                                    ...prev,
                                    driveId: true,
                                  }));
                                }
                              }
                            }}
                            onBlur={() => {
                              setPopupField(null);
                              if (errors.driveId) {
                                setBlurredFields((prev) =>
                                  new Set(prev).add("driveId"),
                                );
                              }
                            }}
                            placeholder="Enter G-Drive ID"
                          />
                          {popupField === "driveId" && errors.driveId && (
                            <div className="absolute z-10 w-full">
                              <FieldError message={errors.driveId} />
                            </div>
                          )}
                          {blurredFields.has("driveId") && errors.driveId && (
                            <span className="mt-1 text-xs text-red-500">
                              Required
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
              {(drivePreset || editingDrive) && (
                <div className="absolute bottom-6 left-0 right-0 flex flex-col gap-3 border-t border-gray-700 px-4 pt-6 sm:flex-row sm:items-end sm:justify-end md:pr-6">
                  {editingDrive && (
                    <div className="relative w-full sm:w-auto">
                      {confirmDelete ? (
                        <div className="flex w-full items-center gap-2 sm:w-auto">
                          <button
                            onClick={() => setConfirmDelete(false)}
                            className="flex flex-1 items-center justify-center rounded-md bg-gray-700 px-4 py-2 text-red-400 transition-colors hover:bg-gray-600 hover:text-red-300 sm:flex-none"
                          >
                            <X size={16} />
                          </button>
                          <button
                            onClick={handleDeleteDrive}
                            disabled={isLoading}
                            className="flex flex-1 items-center justify-center rounded-md bg-gray-700 px-4 py-2 text-green-400 transition-colors hover:bg-gray-600 hover:text-green-300 disabled:opacity-50 sm:flex-none"
                          >
                            <Check size={16} />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmDelete(true)}
                          disabled={isLoading}
                          className="flex w-full items-center justify-center rounded-md bg-red-600 px-4 py-2 text-sm text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                        >
                          Remove
                        </button>
                      )}
                      {confirmDelete && (
                        <div className="absolute bottom-full left-0 mb-2 whitespace-nowrap rounded-md border border-gray-800 bg-gray-950 px-3 py-1.5">
                          <span className="text-xs text-gray-400">
                            Are you sure?
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                  <button
                    onClick={handleCancel}
                    disabled={isLoading}
                    className="w-full rounded-md bg-gray-700 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                  >
                    {isLoading ? "Cancelling..." : "Cancel"}
                  </button>
                  <button
                    onClick={handleSaveDrive}
                    disabled={
                      isLoading ||
                      (driveInitialState !== null && !driveHasChanges)
                    }
                    className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                  >
                    {isLoading
                      ? "Saving..."
                      : driveInitialState !== null && !driveHasChanges
                        ? "No Changes"
                        : "Save"}
                  </button>
                </div>
              )}
            </>
          ) : (
            <>
              <div className="border-b border-gray-700 p-4 md:p-6">
                <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-center gap-2 sm:pt-2">
                    <label className="text-sm text-white">Auth Method</label>
                    <div className="relative flex items-center">
                      <Info
                        size={14}
                        className="text-gray-400 hover:text-white"
                        onMouseEnter={() => showToolTip("rcloneConfig")}
                        onMouseLeave={hideTooltip}
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveTooltip(
                            activeTooltip === "rcloneConfig"
                              ? null
                              : "rcloneConfig",
                          );
                        }}
                      />
                      {activeTooltip === "rcloneConfig" && (
                        <div
                          className="absolute left-full top-1/2 z-10 ml-2 mt-1 w-60 -translate-y-1/2 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-gray-300 shadow-lg sm:w-96"
                          onMouseEnter={cancelHide}
                          onMouseLeave={hideTooltip}
                        >
                          <span className="text-xs text-gray-300">
                            Please read the rclone configuration guide here.
                            <br />
                            <br />
                          </span>
                          <a
                            className="break-all text-blue-400"
                            href="https://github.com/Drazzilb08/daps/wiki/rclone-configuration"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            https://github.com/Drazzilb08/daps/wiki/rclone-configuration
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="relative sm:w-80">
                    <select
                      value={authMethod}
                      onChange={(e) => {
                        const newMethod = e.target.value;
                        setAuthMethod(newMethod);
                        setErrors({});
                        setBlurredFields(new Set());
                        if (newMethod === "oAuth") {
                          setServiceAccount("");
                          setClientId(authInitialState?.clientId || "");
                          setClientSecret(authInitialState?.clientSecret || "");
                          setOauthToken(authInitialState?.oAuthToken || "");
                          setShowToken(!authInitialState?.oAuthToken);
                        } else if (newMethod === "serviceAccount") {
                          setClientId("");
                          setClientSecret("");
                          setOauthToken("");
                          setShowToken(true);
                          setServiceAccount(
                            authInitialState?.serviceAccount || "",
                          );
                        } else {
                          setClientId("");
                          setClientSecret("");
                          setOauthToken("");
                          setShowToken(true);
                          setServiceAccount("");
                        }
                      }}
                      className="w-full cursor-pointer appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                      onBlur={() => setPopupField(null)}
                    >
                      <option value="">Select Type</option>
                      <option value="oAuth">OAuth</option>
                      <option value="serviceAccount">Service Account</option>
                    </select>
                    <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                      <ChevronDown size={18} />
                    </div>
                  </div>
                </div>
              </div>
              {authMethod === "oAuth" && (
                <>
                  <div className="p-4 md:p-6">
                    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex items-center gap-2 sm:pt-2">
                        <label className="text-sm text-white">Client Id</label>
                        <span className="text-red-500">*</span>
                      </div>
                      <div className="flex flex-col gap-1 sm:w-80">
                        <div className="relative">
                          <input
                            className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("clientId") && errors.clientId ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                            type="text"
                            value={clientId}
                            ref={clientIdRef}
                            onChange={(e) => {
                              setClientId(e.target.value);
                              if (
                                blurredFields.has("clientId") ||
                                errors.clientId
                              ) {
                                if (e.target.value.trim()) {
                                  setErrors((prev) => ({
                                    ...prev,
                                    clientId: null,
                                  }));
                                } else {
                                  setErrors((prev) => ({
                                    ...prev,
                                    clientId: true,
                                  }));
                                }
                              }
                            }}
                            onBlur={() => {
                              setPopupField(null);
                              if (errors.clientId) {
                                setBlurredFields((prev) =>
                                  new Set(prev).add("clientId"),
                                );
                              }
                            }}
                            placeholder="asdasds.apps.googleusercontent.com"
                          />
                          {popupField === "clientId" && errors.clientId && (
                            <div className="absolute z-10 w-full">
                              <FieldError message={errors.clientId} />
                            </div>
                          )}
                          {blurredFields.has("clientId") && errors.clientId && (
                            <span className="mt-1 text-xs text-red-500">
                              Required
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 md:p-6">
                    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex items-center gap-2 sm:pt-2">
                        <label className="text-sm text-white">
                          Client Secret
                        </label>
                        <span className="text-red-500">*</span>
                      </div>
                      <div className="flex flex-col gap-1 sm:w-80">
                        <div className="relative">
                          <input
                            className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("clientSecret") && errors.clientSecret ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                            type={showClientSecret ? "text" : "password"}
                            value={clientSecret}
                            ref={clientSecretRef}
                            onChange={(e) => {
                              setClientSecret(e.target.value);
                              if (
                                blurredFields.has("clientSecret") ||
                                errors.clientSecret
                              ) {
                                if (e.target.value.trim()) {
                                  setErrors((prev) => ({
                                    ...prev,
                                    clientSecret: null,
                                  }));
                                } else {
                                  setErrors((prev) => ({
                                    ...prev,
                                    clientSecret: true,
                                  }));
                                }
                              }
                            }}
                            onBlur={() => {
                              setPopupField(null);
                              if (errors.clientSecret) {
                                setBlurredFields((prev) =>
                                  new Set(prev).add("clientSecret"),
                                );
                              }
                            }}
                            placeholder="GOCSPX-asda123"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowClientSecret(!showClientSecret)
                            }
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 transition-colors hover:text-white"
                          >
                            {showClientSecret ? (
                              <EyeOff size={18} />
                            ) : (
                              <Eye size={18} />
                            )}
                          </button>
                          {popupField === "clientSecret" &&
                            errors.clientSecret && (
                              <div className="absolute z-10 w-full">
                                <FieldError message={errors.clientSecret} />
                              </div>
                            )}
                        </div>
                        {blurredFields.has("clientSecret") &&
                          errors.clientSecret && (
                            <span className="mt-1 text-xs text-red-500">
                              Required
                            </span>
                          )}
                      </div>
                    </div>
                  </div>
                  <div className="p-4 md:p-6">
                    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex items-center gap-2 sm:pt-2">
                        <label className="text-sm text-white">
                          OAuth Token
                        </label>
                        <span className="text-red-500">*</span>
                      </div>
                      <div className="flex flex-col gap-1 sm:w-80">
                        <div className="relative">
                          <textarea
                            className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white transition-all focus:outline-none focus:ring-2 ${!showToken && rcloneConfigured ? "select-none blur-sm" : ""} ${blurredFields.has("oAuthToken") && errors.oAuthToken ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                            rows={6}
                            value={oAuthToken}
                            ref={oAuthTokenRef}
                            onChange={(e) => {
                              setOauthToken(e.target.value);
                              if (
                                blurredFields.has("oAuthToken") ||
                                errors.oAuthToken
                              ) {
                                if (e.target.value.trim()) {
                                  setErrors((prev) => ({
                                    ...prev,
                                    oAuthToken: null,
                                  }));
                                } else {
                                  setErrors((prev) => ({
                                    ...prev,
                                    oAuthToken: true,
                                  }));
                                }
                              }
                            }}
                            onBlur={() => {
                              setPopupField(null);
                              if (errors.oAuthToken) {
                                setBlurredFields((prev) =>
                                  new Set(prev).add("oAuthToken"),
                                );
                              }
                            }}
                            placeholder={tokenPlaceholder}
                          />
                          <button
                            type="button"
                            onClick={() => setShowToken(!showToken)}
                            className="absolute right-2 top-2 p-1 text-gray-400 transition-colors hover:text-white"
                          >
                            {showToken ? (
                              <EyeOff size={18} />
                            ) : (
                              <Eye size={18} />
                            )}
                          </button>
                        </div>
                        {popupField === "oAuthToken" && errors.oAuthToken && (
                          <div className="absolute z-10 w-full">
                            <FieldError message={errors.oAuthToken} />
                          </div>
                        )}
                        {blurredFields.has("oAuthToken") &&
                          errors.oAuthToken && (
                            <span className="mt-1 text-xs text-red-500">
                              Required
                            </span>
                          )}
                      </div>
                    </div>
                  </div>
                </>
              )}
              {authMethod === "serviceAccount" && (
                <div className="p-4 md:p-6">
                  <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-center gap-2 sm:pt-2">
                      <label className="text-sm text-white">
                        Service Account
                      </label>
                      <span className="text-red-500">*</span>
                    </div>
                    <div className="flex flex-col gap-1 sm:w-80">
                      <div className="relative">
                        <input
                          className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("serviceAccount") && errors.serviceAccount ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                          type="text"
                          value={serviceAccount}
                          ref={serviceAccountRef}
                          onChange={(e) => {
                            setServiceAccount(e.target.value);
                            if (
                              blurredFields.has("serviceAccount") ||
                              errors.serviceAccount
                            ) {
                              if (e.target.value.trim()) {
                                setErrors((prev) => ({
                                  ...prev,
                                  serviceAccount: null,
                                }));
                              } else {
                                setErrors((prev) => ({
                                  ...prev,
                                  serviceAccount: true,
                                }));
                              }
                            }
                          }}
                          onBlur={() => {
                            setPopupField(null);
                            if (errors.serviceAccount) {
                              setBlurredFields((prev) =>
                                new Set(prev).add("serviceAccount"),
                              );
                            }
                          }}
                          placeholder="/config/rclone_sa.json"
                        />
                        {popupField === "serviceAccount" &&
                          errors.serviceAccount && (
                            <div className="absolute z-10 w-full">
                              <FieldError message={errors.serviceAccount} />
                            </div>
                          )}
                        {blurredFields.has("serviceAccount") &&
                          errors.serviceAccount && (
                            <span className="mt-1 text-xs text-red-500">
                              Required
                            </span>
                          )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {authMethod && (
                <div className="absolute bottom-6 left-0 right-0 flex flex-col gap-3 border-t border-gray-700 px-4 pt-6 sm:flex-row sm:items-end sm:justify-end md:pr-6">
                  <button
                    onClick={handleSaveAuth}
                    disabled={
                      isLoading ||
                      (authInitialState !== null && !sidebarHasChanges)
                    }
                    className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                  >
                    {isLoading
                      ? "Saving..."
                      : authInitialState !== null && !sidebarHasChanges
                        ? "No Changes"
                        : "Save"}
                  </button>
                  <button
                    onClick={handleCancel}
                    disabled={isLoading}
                    className="w-full rounded-md bg-gray-700 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                  >
                    {isLoading ? "Cancelling..." : "Cancel"}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
        <div className="mt-4 flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
          <button
            onClick={handleSaveForm}
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
            onClick={() => {
              setAuthInitialState({
                authMethod,
                clientId,
                clientSecret,
                oAuthToken,
                serviceAccount,
              });
              setIsSidebarOpen(true);
            }}
            className="flex items-center justify-center gap-2 rounded-md bg-gray-500 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 sm:justify-start"
          >
            {rcloneConfigured ? "Edit Config" : "Configure"}
          </button>
        </div>
      </div>
      {/* Overlay */}
      {isSidebarOpen && (
        <div
          onClick={handleCancel}
          className="fixed inset-0 z-[55] bg-black bg-opacity-50"
        ></div>
      )}
    </div>
  );
};
export default DriveSyncSettings;
