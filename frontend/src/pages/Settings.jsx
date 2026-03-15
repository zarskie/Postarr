import { useMemo, useEffect, useState, useRef } from "react";
import { isValidCron } from "cron-validator";
import FieldError from "../components/common/FieldError";
import {
  KeyRound,
  Calendar,
  Plus,
  X,
  Check,
  Eye,
  EyeOff,
  ChevronDown,
  Bell,
  Settings2,
  Info,
} from "lucide-react";
import PosterRenamerrSettings from "../components/settings/PosterRenamerrSettings";
import UnmatchedAssetsSettings from "../components/settings/UnmatchedAssetsSettings";
import PlexUploaderrSettings from "../components/settings/PlexUploaderrSettings";
import DriveSyncSettings from "../components/settings/DriveSyncSettings";
import UnsavedChanges from "../components/common/UnsavedChanges";

function isValidCronExpression(value) {
  return isValidCron(value, { seconds: false, allowBlankDay: true });
}
function getIntervalError(value) {
  const num = Number(value);
  if (!Number.isInteger(num) || num <= 0)
    return "Must be a positive whole number";
  if (num > 10800) return "Interval is too high (max 10080 minutes)";
  return null;
}

function Settings() {
  const instanceNameRef = useRef(null);
  const urlRef = useRef(null);
  const apiKeyRef = useRef(null);
  const scheduleValueRef = useRef(null);
  const tooltipTimeout = useRef(null);

  const [activeSection, setActiveSection] = useState("instances");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [selectedType, setSelectedType] = useState("");
  const [instanceName, setInstanceName] = useState("");
  const [url, setUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [instances, setInstances] = useState([]);
  const [connectionTested, setConnectionTested] = useState(false);
  const [editingInstance, setEditingInstance] = useState(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [errors, setErrors] = useState({});
  const [popupField, setPopupField] = useState(null);
  const [showTestWarning, setShowTestWarning] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [scheduleType, setScheduleType] = useState("cron");
  const [selectedScheduleModule, setSelectedScheduleModule] = useState("");
  const [selectedSettingsModule, setSelectedSettingsModule] = useState("");
  const [scheduleValue, setScheduleValue] = useState("");
  const [currentSchedule, setCurrentSchedule] = useState(null);
  const [blurredFields, setBlurredFields] = useState(new Set());
  const [scheduleInitialState, setScheduleInitialState] = useState(null);
  const [instanceInitialState, setInstanceInitialState] = useState(null);
  const [renamerrDirty, setRenamerrDirty] = useState(false);
  const [unmatchedDirty, setUnmatchedDirty] = useState(false);
  const [plexUploaderrDirty, setPlexUploaderrDirty] = useState(false);
  const [driveSyncDirty, setDriveSyncDirty] = useState(false);
  const [pendingSection, setPendingSection] = useState(null);
  const [renamerrResetKey, setRenamerrResetKey] = useState(0);
  const [unmatchedResetKey, setUnmatchedResetKey] = useState(0);
  const [plexUploaderrResetKey, setPlexUploaderrResetKey] = useState(0);
  const [driveSyncResetKey, setDriveSyncResetKey] = useState(0);
  const [pendingAction, setPendingAction] = useState(null);
  const [activeTooltip, setActiveTooltip] = useState(null);

  const sections = [
    { id: "instances", label: "Instances", icon: KeyRound },
    { id: "schedule", label: "Schedule", icon: Calendar },
    { id: "settings", label: "Settings", icon: Settings2 },
    { id: "notifications", label: "Notifications", icon: Bell },
  ];
  const moduleNames = {
    "poster-renamerr": "Poster Renamerr",
    "unmatched-assets": "Unmatched Assets",
    "plex-uploaderr": "Plex Uploaderr",
    "drive-sync": "Drive Sync",
  };

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

  const handleSaveInstance = async () => {
    const newErrors = {};
    if (!instanceName) newErrors.instanceName = true;
    if (!url) newErrors.url = true;
    if (!apiKey) newErrors.apiKey = true;

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      if (newErrors.instanceName) {
        setPopupField("instanceName");
        instanceNameRef.current?.focus();
      } else if (newErrors.url) {
        setPopupField("url");
        urlRef.current?.focus();
      } else if (newErrors.apiKey) {
        apiKeyRef.current?.focus();
        setPopupField("apiKey");
      }
      return;
    }
    if (!connectionTested) {
      setShowTestWarning(true);
      setTimeout(() => setShowTestWarning(false), 3000);
      return;
    }
    setErrors({});
    setIsLoading(true);
    try {
      const endpoint = editingInstance
        ? "/api/settings/update-instance"
        : "/api/settings/add-instance";
      const body = editingInstance
        ? {
            type: selectedType,
            id: editingInstance.id,
            instanceName: instanceName,
            url: url,
            apiKey: apiKey,
          }
        : {
            type: selectedType,
            instanceName: instanceName,
            url: url,
            apiKey: apiKey,
          };
      const response = await fetch(endpoint, {
        method: editingInstance ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (response.ok) {
        setIsSidebarOpen(false);
        setEditingInstance(null);
        setSelectedType("");
        setInstanceName("");
        setUrl("");
        setApiKey("");
        setConnectionStatus(null);
        setConnectionTested(false);
        setErrors({});
        setBlurredFields(new Set());
        setShowApiKey(false);
        fetchInstances();
      } else {
        setConnectionStatus({
          success: false,
          message: result.message,
        });
      }
    } catch (error) {
      console.error("Error saving instance", error);
      setConnectionStatus({
        success: false,
        message: error.message,
      });
    } finally {
      setIsLoading(false);
      setTimeout(() => setConnectionStatus(null), 3000);
    }
  };
  const handleEditInstance = (instance) => {
    setEditingInstance(instance);
    setSelectedType(instance.type);
    setInstanceName(instance.name);
    setUrl(instance.url);
    setApiKey(instance.apiKey);
    setInstanceInitialState({
      instanceName: instance.name,
      url: instance.url,
      apiKey: instance.apiKey,
    });
    setConnectionStatus(null);
    setShowApiKey(false);
    setConnectionTested(true);
    setErrors({});
    setBlurredFields(new Set());
    setIsSidebarOpen(true);
    setShowTestWarning(false);
  };
  const handleCancelInstance = () => {
    setIsSidebarOpen(false);
    setEditingInstance(null);
    setSelectedType("");
    setInstanceName("");
    setUrl("");
    setApiKey("");
    setConnectionStatus(null);
    setShowApiKey(false);
    setShowTestWarning(false);
    setConnectionTested(false);
    setErrors({});
    setBlurredFields(new Set());
    fetchInstances();
    setConfirmDelete(false);
    setInstanceInitialState(null);
  };
  const handleDeleteInstance = async () => {
    if (!editingInstance) return;
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch("/api/settings/delete-instance", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          type: editingInstance.type,
          id: editingInstance.id,
        }),
      });
      const result = await response.json();
      if (response.ok) {
        setIsSidebarOpen(false);
        setEditingInstance(null);
        setSelectedType("");
        setInstanceName("");
        setUrl("");
        setApiKey("");
        setConnectionStatus(null);
        setShowApiKey(false);
        setConnectionTested(false);
        setErrors({});
        setBlurredFields(new Set());
        fetchInstances();
        setShowTestWarning(false);
        setConfirmDelete(false);
      } else {
        alert(`Error: ${result.message}`);
      }
    } catch (error) {
      console.error("Error deleting instance:", error);
      alert("Error connecting to server");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchInstances = async () => {
    try {
      const response = await fetch("/api/settings/get-instances");
      const result = await response.json();
      if (result.success) {
        const sorted = [...result.instances].sort((a, b) =>
          a.type.localeCompare(b.type),
        );
        setInstances(sorted);
      }
    } catch (error) {
      console.error("Error fetching instances:", error);
    }
  };

  const handleTestConnection = async () => {
    const newErrors = {};
    if (!instanceName) newErrors.instanceName = true;
    if (!url) newErrors.url = true;
    if (!apiKey) newErrors.apiKey = true;

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      if (newErrors.instanceName) {
        setPopupField("instanceName");
        instanceNameRef.current?.focus();
      } else if (newErrors.url) {
        setPopupField("url");
        urlRef.current?.focus();
      } else if (newErrors.apiKey) {
        apiKeyRef.current?.focus();
        setPopupField("apiKey");
      }
      return;
    }
    setIsLoading(true);
    setConnectionStatus(null);
    setConnectionTested(false);
    try {
      const response = await fetch("/api/settings/test-connection", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          type: selectedType,
          url: url,
          apiKey: apiKey,
        }),
      });

      if (response.ok) {
        setConnectionStatus({
          success: true,
        });
        setConnectionTested(true);
        setShowTestWarning(false);
      } else {
        setConnectionStatus({
          success: false,
          message: "Error connecting to server",
        });
        setConnectionTested(false);
      }
    } catch (error) {
      console.error("Error testing connection:", error);
      setConnectionStatus({
        success: false,
        message: error.message,
      });
      setConnectionTested(false);
    } finally {
      setIsLoading(false);
      setTimeout(() => setConnectionStatus(null), 3000);
    }
  };
  const handleSaveSchedule = async () => {
    const newErrors = {};
    if (!scheduleValue) {
      newErrors.scheduleValue = "Please fill out this field";
    } else if (
      scheduleType === "cron" &&
      !isValidCronExpression(scheduleValue)
    ) {
      newErrors.scheduleValue = "Invalid cron expression";
    } else if (scheduleType === "interval") {
      const intervalError = getIntervalError(scheduleValue);
      if (intervalError) newErrors.scheduleValue = intervalError;
    }
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setPopupField("scheduleValue");
      scheduleValueRef.current?.focus();
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch("/api/settings/add-schedule", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          module: selectedScheduleModule,
          scheduleType: scheduleType,
          scheduleValue: scheduleValue,
        }),
      });
      const data = await response.json();
      if (data.success) {
        fetchCurrentSchedule(selectedScheduleModule);
        setScheduleInitialState({
          scheduleType: scheduleType,
          scheduleValue: scheduleValue.trim(),
        });
      } else {
        alert("Error: " + data.message);
      }
    } catch (error) {
      console.error("Save failed:", error);
      alert("Failed to connect to the server");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSchedule = async () => {
    if (!selectedScheduleModule) return;
    try {
      const response = await fetch(
        `/api/settings/delete-schedule/${selectedScheduleModule}`,
        {
          method: "POST",
        },
      );
      const data = await response.json();
      if (data.success) {
        setCurrentSchedule(null);
        setScheduleValue("");
        setScheduleType("cron");
        setScheduleInitialState({
          scheduleType: "cron",
          scheduleValue: "",
        });
        setErrors({});
        setBlurredFields(new Set());
        setPopupField(null);
      }
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };
  const fetchCurrentSchedule = async (moduleName) => {
    if (!moduleName) {
      setCurrentSchedule(null);
      setScheduleValue("");
      return;
    }
    try {
      const response = await fetch(`/api/settings/get-schedule/${moduleName}`);
      const result = await response.json();
      if (result.success && result.data) {
        const d = result.data;
        setCurrentSchedule(d);
        setScheduleType(d.schedule_type || "cron");
        setScheduleValue(d.schedule_value || "");
        setScheduleInitialState({
          scheduleType: d.schedule_type || "cron",
          scheduleValue: d.schedule_value || "",
        });
      } else {
        setCurrentSchedule(null);
        setScheduleType("cron");
        setScheduleValue("");
      }
    } catch (error) {
      setCurrentSchedule(null);
      setScheduleType("cron");
      setScheduleValue("");
      console.error("Error fetching schedule:", error);
    }
  };

  const hasChanges = useMemo(() => {
    if (activeSection === "schedule") {
      if (!scheduleInitialState) return true;
      return (
        scheduleValue !== scheduleInitialState.scheduleValue ||
        scheduleType !== scheduleInitialState.scheduleType
      );
    }
    if (editingInstance) {
      if (!instanceInitialState) return true;
      return (
        instanceName !== instanceInitialState.instanceName ||
        url !== instanceInitialState.url ||
        apiKey !== instanceInitialState.apiKey
      );
    }
    return true;
  }, [
    activeSection,
    scheduleInitialState,
    instanceInitialState,
    editingInstance,
    instanceName,
    url,
    apiKey,
    scheduleValue,
    scheduleType,
  ]);

  const unsavedSections = useMemo(() => {
    const result = new Set();
    if (
      currentSchedule &&
      scheduleInitialState &&
      (scheduleValue !== scheduleInitialState.scheduleValue ||
        scheduleType !== scheduleInitialState.scheduleType)
    ) {
      result.add("schedule");
    }
    if (
      renamerrDirty ||
      unmatchedDirty ||
      plexUploaderrDirty ||
      driveSyncDirty
    ) {
      result.add("settings");
    }
    return result;
  }, [
    currentSchedule,
    scheduleInitialState,
    scheduleValue,
    scheduleType,
    renamerrDirty,
    unmatchedDirty,
    plexUploaderrDirty,
    driveSyncDirty,
  ]);

  const handleDiscard = () => {
    if (pendingAction) {
      if (activeSection === "schedule") {
        if (scheduleInitialState) {
          setScheduleType(scheduleInitialState.scheduleType);
          setScheduleValue(scheduleInitialState.scheduleValue);
        }
      }
      if (activeSection === "settings") {
        if (selectedSettingsModule === "poster-renamerr-settings") {
          setRenamerrDirty(false);
          setRenamerrResetKey((k) => k + 1);
        }
        if (selectedSettingsModule === "unmatched-assets-settings") {
          setUnmatchedDirty(false);
          setUnmatchedResetKey((k) => k + 1);
        }
        if (selectedSettingsModule === "plex-uploaderr-settings") {
          setPlexUploaderrDirty(false);
          setPlexUploaderrResetKey((k) => k + 1);
        }
        if (selectedSettingsModule === "drive-sync-settings") {
          setDriveSyncDirty(false);
          setDriveSyncResetKey((k) => k + 1);
        }
      }
      pendingAction();
      setPendingAction(null);
      setPendingSection(null);
      return;
    }
    if (activeSection === "schedule") {
      if (scheduleInitialState) {
        setScheduleType(scheduleInitialState.scheduleType);
        setScheduleValue(scheduleInitialState.scheduleValue);
      }
    }
    if (activeSection === "settings") {
      if (selectedSettingsModule === "poster-renamerr-settings") {
        setRenamerrDirty(false);
        setRenamerrResetKey((k) => k + 1);
      }
      if (selectedSettingsModule === "unmatched-assets-settings") {
        setUnmatchedDirty(false);
        setUnmatchedResetKey((k) => k + 1);
      }
      if (selectedSettingsModule === "plex-uploaderr-settings") {
        setPlexUploaderrDirty(false);
        setPlexUploaderrResetKey((k) => k + 1);
      }
      if (selectedSettingsModule === "drive-sync-settings") {
        setDriveSyncDirty(false);
        setDriveSyncResetKey((k) => k + 1);
      }
    }
    setActiveSection(pendingSection);
    setPendingSection(null);
  };

  const handleStay = () => {
    setPendingSection(null);
    setPendingAction(null);
  };

  useEffect(() => {
    fetchInstances();
  }, []);

  useEffect(() => {
    fetchCurrentSchedule(selectedScheduleModule);
  }, [selectedScheduleModule]);

  return (
    <div>
      <div className="pointer-events-none fixed right-4 top-4 z-[60] flex flex-col gap-2">
        {connectionStatus && (
          <div
            className={`animate-in fade-in slide-in-from-right-10 flex transform items-center gap-3 rounded-lg border px-4 py-3 shadow-2xl transition-all duration-500 ease-in-out ${connectionStatus.success ? "border-green-500 bg-gray-800 text-green-400" : "border-red-500 bg-gray-800 text-red-400"}`}
          >
            <div
              className={`rounded-full p-1 ${connectionStatus.success ? "bg-green-500/20" : "bg-red-500/20"}`}
            >
              {connectionStatus.success ? (
                <Check size={16} className="text-green-400" />
              ) : (
                <X size={16} className="text-red-400" />
              )}
            </div>
            <span className="text-sm font-medium">
              {connectionStatus.success
                ? "Connection Successful!"
                : connectionStatus.message || "Connection Failed!"}
            </span>
          </div>
        )}
      </div>
      <h1 className="mb-6 px-2 text-2xl font-bold text-white md:px-0">
        Settings
      </h1>
      <div className="mx-2 flex flex-col rounded-lg bg-gray-800 py-2 md:mx-0 md:flex-row">
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
                      const leavingDirtySchedule =
                        activeSection === "schedule" &&
                        section.id !== "schedule" &&
                        unsavedSections.has("schedule");
                      const leavingDirtySettings =
                        activeSection === "settings" &&
                        section.id !== "settings" &&
                        unsavedSections.has("settings");
                      if (leavingDirtySchedule || leavingDirtySettings) {
                        setPendingSection(section.id);
                        return;
                      }
                      setActiveSection(section.id);
                    }}
                    className={`relative flex w-full items-center gap-3 whitespace-nowrap px-4 py-2 text-left transition-colors ${
                      activeSection === section.id
                        ? "bg-gray-700 text-white"
                        : "text-gray-400 hover:bg-gray-700 hover:text-white"
                    }`}
                  >
                    <span
                      className={`absolute left-0 top-0 h-full w-1 rounded-r ${isActive ? "bg-blue-500" : "bg-transparent"}`}
                    />
                    <Icon size={22} />
                    <span className="flex-1">{section.label}</span>
                    {unsavedSections.has(section.id) && (
                      <span
                        className="h-2 w-2 rounded-full bg-yellow-400"
                        title="Unsaved changes"
                      />
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
        {/* Right Content Area */}
        <div className="flex-1 p-4 md:p-6">
          {activeSection === "instances" && (
            <div>
              <div className="mb-6 flex flex-col gap-3 border-b border-gray-700 pb-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="mb-2 text-xl font-semibold text-white">
                    Instances
                  </h2>
                  <p className="mb-4 text-sm text-gray-400">
                    Configure radarr, sonarr and plex instances.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setShowApiKey(false);
                    setErrors({});
                    setIsSidebarOpen(true);
                  }}
                  className="flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 sm:justify-start"
                >
                  <Plus size={18} />
                  Add New
                </button>
              </div>
              {/* Instance List */}
              <div className="space-y-3">
                {instances.length === 0 ? (
                  <p className="text-sm text-gray-400">
                    No instances configured yet.
                  </p>
                ) : (
                  instances.map((instance) => (
                    <div
                      key={`${instance.type}-${instance.id}`}
                      className="flex flex-col gap-3 rounded-lg bg-gray-700 p-4 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex-1">
                        <div className="mb-1 flex flex-wrap items-center gap-2">
                          <span className="font-medium text-white">
                            {instance.name}
                          </span>
                          <span className="rounded bg-gray-600 px-2 py-1 text-xs uppercase text-gray-300">
                            {instance.type}
                          </span>
                        </div>
                        <p className="break-all text-sm text-gray-400">
                          {instance.url}
                        </p>
                      </div>
                      <button
                        onClick={() => handleEditInstance(instance)}
                        className="w-full rounded-md bg-gray-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-gray-500 sm:w-auto"
                      >
                        Edit
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
          {activeSection === "schedule" && (
            <div>
              <div className="mb-6 flex flex-col gap-3 border-b border-gray-700 pb-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="mb-2 text-xl font-semibold text-white">
                    Schedule
                  </h2>
                  <p className="mb-4 text-sm text-gray-400">
                    Configure schedule for modules.
                  </p>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-medium text-gray-400">
                    Select Module
                  </h3>
                  <div className="relative w-full sm:w-64">
                    <select
                      value={selectedScheduleModule}
                      onChange={(e) => {
                        const newModule = e.target.value;
                        if (unsavedSections.has("schedule")) {
                          setPendingSection(activeSection);
                          setPendingAction(() => () => {
                            setSelectedScheduleModule(newModule);
                            setScheduleInitialState(null);
                            setErrors({});
                            setBlurredFields(new Set());
                          });
                          return;
                        }
                        setSelectedScheduleModule(newModule);
                        setScheduleInitialState(null);
                        setErrors({});
                        setBlurredFields(new Set());
                      }}
                      className="w-full appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 sm:w-64"
                    >
                      <option value="">Choose a module</option>
                      <option value="poster-renamerr">Poster Renamerr</option>
                      <option value="unmatched-assets">Unmatched Assets</option>
                      <option value="plex-uploaderr">Plex Uploaderr</option>
                      <option value="drive-sync">Drive Sync</option>
                    </select>
                    <ChevronDown
                      size={18}
                      className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                    />
                  </div>
                </div>
              </div>
              {selectedScheduleModule ? (
                <>
                  <h2 className="mb-4 text-xl font-semibold text-white">
                    {moduleNames[selectedScheduleModule] ||
                      selectedScheduleModule}
                  </h2>
                  <div className="mb-4 grid grid-cols-1 gap-4 rounded-lg bg-gray-700 p-4 sm:grid-cols-3">
                    <div className="col-span-1 sm:col-span-3">
                      <h3 className="text-sm font-medium text-white">
                        Current Schedule
                      </h3>
                    </div>
                    <div>
                      <h3 className="mb-2 text-sm font-medium text-gray-400">
                        Type
                      </h3>
                      <div className="rounded-md bg-gray-600 p-2">
                        <p className="text-sm text-white">
                          {currentSchedule?.schedule_type || "N/A"}
                        </p>
                      </div>
                    </div>
                    <div>
                      <h3 className="mb-2 text-sm font-medium text-gray-400">
                        Value
                      </h3>
                      <div className="rounded-md bg-gray-600 p-2">
                        <p className="text-sm text-white">
                          {currentSchedule?.schedule_value || "N/A"}
                        </p>
                      </div>
                    </div>
                    <div>
                      <h3 className="mb-2 text-sm font-medium text-gray-400">
                        Next Run
                      </h3>
                      <div className="rounded-md bg-gray-600 p-2">
                        <p className="text-sm text-white">
                          {currentSchedule?.next_run || "N/A"}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="mb-4 flex flex-col gap-2 rounded-lg bg-gray-700 p-4">
                    <h3 className="mb-4 text-sm font-medium text-white">
                      Update Schedule
                    </h3>
                    <h3 className="text-sm font-medium text-gray-400">
                      Schedule Type
                    </h3>
                    <div className="flex flex-row gap-4">
                      <label className="flex cursor-pointer items-center gap-3">
                        <input
                          type="radio"
                          name="scheduleType"
                          value="cron"
                          checked={scheduleType === "cron"}
                          onChange={(e) => {
                            setScheduleType(e.target.value);
                            setErrors({});
                            setBlurredFields(new Set());
                          }}
                          className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <span className="text-sm text-white">
                          Cron Expression
                        </span>
                      </label>
                      <label className="flex cursor-pointer items-center gap-3">
                        <input
                          type="radio"
                          name="scheduleType"
                          value="interval"
                          checked={scheduleType === "interval"}
                          onChange={(e) => {
                            setScheduleType(e.target.value);
                            setErrors({});
                            setBlurredFields(new Set());
                          }}
                          className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                        />
                        <span className="text-sm text-white">
                          Interval (minutes)
                        </span>
                      </label>
                    </div>
                    {scheduleType && (
                      <div className="py-4">
                        <h3 className="mb-2 text-sm font-medium text-gray-400">
                          Schedule Value
                          <span className="text-red-500"> *</span>
                        </h3>
                        <div className="relative">
                          <input
                            value={scheduleValue}
                            ref={scheduleValueRef}
                            onChange={(e) => {
                              setScheduleValue(e.target.value);
                              if (
                                blurredFields.has("scheduleValue") ||
                                errors.scheduleValue
                              ) {
                                if (e.target.value.trim()) {
                                  setErrors((prev) => ({
                                    ...prev,
                                    scheduleValue: null,
                                  }));
                                } else {
                                  setErrors((prev) => ({
                                    ...prev,
                                    scheduleValue: true,
                                  }));
                                }
                              }
                            }}
                            onBlur={() => {
                              setPopupField(null);
                              if (errors.scheduleValue) {
                                setBlurredFields((prev) =>
                                  new Set(prev).add("scheduleValue"),
                                );
                              }
                            }}
                            type="text"
                            className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("scheduleValue") && errors.scheduleValue ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                            placeholder={
                              scheduleType === "cron" ? "0 */6 * * *" : "15"
                            }
                          />
                          {popupField === "scheduleValue" &&
                            errors.scheduleValue && (
                              <div className="absolute z-10 w-full">
                                <FieldError message={errors.scheduleValue} />
                              </div>
                            )}
                          {blurredFields.has("scheduleValue") &&
                            errors.scheduleValue && (
                              <span className="mt-1 text-xs text-red-500">
                                Required
                              </span>
                            )}
                        </div>
                        <p className="mt-2 text-xs text-gray-400">
                          {scheduleType === "cron"
                            ? "Enter a valid cron expression (e.g., 0 */6 * * * runs every 6 hours)"
                            : "Enter interval in minutes (e.g., 15 runs every 15 minutes)"}
                        </p>
                      </div>
                    )}
                    <div className="border-t border-gray-500 pt-4">
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <button
                          onClick={handleSaveSchedule}
                          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                          disabled={isLoading || !hasChanges}
                        >
                          {isLoading
                            ? "Saving..."
                            : !hasChanges
                              ? "No Changes"
                              : "Save"}
                        </button>
                        <button
                          onClick={() => {
                            setScheduleValue("");
                            setErrors({});
                            setBlurredFields(new Set());
                          }}
                          className="w-full rounded-md bg-gray-500 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                          disabled={isLoading}
                        >
                          {isLoading ? "Resetting..." : "Reset"}
                        </button>
                        <button
                          onClick={handleDeleteSchedule}
                          className="w-full rounded-md bg-gray-500 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                          disabled={isLoading || !currentSchedule}
                        >
                          {isLoading ? "Disabling..." : "Disable"}
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-400">Please select a module.</p>
              )}
            </div>
          )}
          <div className={activeSection === "settings" ? "" : "hidden"}>
            <div className="mb-6 flex flex-col gap-3 border-b border-gray-700 pb-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="mb-2 text-xl font-semibold text-white">
                  Settings
                </h2>
                <p className="mb-4 text-sm text-gray-400">
                  Configure settings for modules.
                </p>
              </div>
              <div>
                <h3 className="mb-2 text-sm font-medium text-gray-400">
                  Select Module
                </h3>
                <div className="relative w-full sm:w-64">
                  <select
                    value={selectedSettingsModule}
                    onChange={(e) => {
                      const newModule = e.target.value;
                      if (unsavedSections.has("settings")) {
                        setPendingSection(activeSection);
                        setPendingAction(() => () => {
                          setSelectedSettingsModule(newModule);
                          setErrors({});
                          setBlurredFields(new Set());
                        });
                        return;
                      }
                      setSelectedSettingsModule(newModule);
                      setErrors({});
                      setBlurredFields(new Set());
                    }}
                    className="w-full appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 sm:w-64"
                  >
                    <option value="">Choose a module</option>
                    <option value="poster-renamerr-settings">
                      Poster Renamerr
                    </option>
                    <option value="unmatched-assets-settings">
                      Unmatched Assets
                    </option>
                    <option value="plex-uploaderr-settings">
                      Plex Uploaderr
                    </option>
                    <option value="drive-sync-settings">Drive Sync</option>
                  </select>
                  <ChevronDown
                    size={18}
                    className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                </div>
              </div>
            </div>
            {/* Render module-specific settings */}
            {selectedSettingsModule ? (
              <div className="mt-4">
                <div
                  className={
                    selectedSettingsModule === "poster-renamerr-settings"
                      ? ""
                      : "hidden"
                  }
                >
                  <PosterRenamerrSettings
                    key={renamerrResetKey}
                    onDirtyChange={setRenamerrDirty}
                  />
                </div>
                <div
                  className={
                    selectedSettingsModule === "unmatched-assets-settings"
                      ? ""
                      : "hidden"
                  }
                >
                  <UnmatchedAssetsSettings
                    key={unmatchedResetKey}
                    onDirtyChange={setUnmatchedDirty}
                  />
                </div>
                <div
                  className={
                    selectedSettingsModule === "plex-uploaderr-settings"
                      ? ""
                      : "hidden"
                  }
                >
                  <PlexUploaderrSettings
                    key={plexUploaderrResetKey}
                    onDirtyChange={setPlexUploaderrDirty}
                  />
                </div>
                <div
                  className={
                    selectedSettingsModule === "drive-sync-settings"
                      ? ""
                      : "hidden"
                  }
                >
                  <DriveSyncSettings
                    key={driveSyncResetKey}
                    onDirtyChange={setDriveSyncDirty}
                  />
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">Please select a module.</p>
            )}
          </div>
        </div>
        {/* Sliding Sidebar */}
        <div
          className={`fixed right-0 top-0 z-50 h-full w-full transform bg-gray-900 shadow-2xl transition-transform duration-300 ease-in-out sm:max-w-xl ${
            isSidebarOpen ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <div className="flex items-start justify-between bg-gray-700 p-6">
            <div className="flex flex-col gap-2">
              <h3 className="text-xl font-semibold text-white">
                {editingInstance ? "Edit Instance" : "Add Instance"}
              </h3>
              <p className="text-sm text-white">
                {editingInstance ? "Edit Instance." : "Add Instance."}
              </p>
            </div>
            <button
              onClick={() => {
                setIsSidebarOpen(false);
                setErrors({});
                setBlurredFields(new Set());
                if (editingInstance) {
                  setEditingInstance("");
                  setSelectedType("");
                  setInstanceName("");
                  setUrl("");
                  setApiKey("");
                  setShowApiKey(false);
                  setConnectionStatus(null);
                  setConnectionTested(false);
                  setShowTestWarning(false);
                  setConfirmDelete(false);
                  setInstanceInitialState(null);
                }
              }}
              className="rounded-md p-1 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
            >
              <X size={24} />
            </button>
          </div>
          <div className="border-b border-gray-700 p-4 md:p-6">
            <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <label className="text-sm text-white sm:pt-2">Type</label>
              <div className="relative sm:w-80">
                <select
                  value={selectedType}
                  disabled={!!editingInstance}
                  onChange={(e) => {
                    setSelectedType(e.target.value);
                    setInstanceName("");
                    setUrl("");
                    setApiKey("");
                    setErrors({});
                    setConnectionStatus(null);
                    setConnectionTested(false);
                    setShowTestWarning(false);
                  }}
                  className="w-full cursor-pointer appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                  onFocus={() => setShowTestWarning(false)}
                  onBlur={() => setPopupField(null)}
                >
                  <option value="">Select type</option>
                  <option value="radarr">Radarr</option>
                  <option value="sonarr">Sonarr</option>
                  <option value="plex">Plex</option>
                </select>
                <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  <ChevronDown size={18} />
                </div>
              </div>
            </div>
          </div>
          {selectedType && (
            <>
              <div className="p-4 md:p-6">
                <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <label className="text-sm text-white sm:pt-2">
                    Name<span className="text-red-500"> *</span>
                  </label>
                  <div className="flex flex-col gap-1 sm:w-80">
                    <div className="relative">
                      <input
                        type="text"
                        value={instanceName}
                        ref={instanceNameRef}
                        onFocus={() => setShowTestWarning(false)}
                        onBlur={() => {
                          setPopupField(null);
                          if (errors.instanceName) {
                            setBlurredFields((prev) =>
                              new Set(prev).add("instanceName"),
                            );
                          }
                        }}
                        onChange={(e) => {
                          setInstanceName(e.target.value);
                          if (
                            blurredFields.has("instanceName") ||
                            errors.instanceName
                          ) {
                            if (e.target.value.trim()) {
                              setErrors((prev) => ({
                                ...prev,
                                instanceName: null,
                              }));
                            } else {
                              setErrors((prev) => ({
                                ...prev,
                                instanceName: true,
                              }));
                            }
                          }
                        }}
                        className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("instanceName") && errors.instanceName ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                        placeholder={
                          selectedType === "radarr"
                            ? "radarr-4k"
                            : selectedType === "sonarr"
                              ? "sonarr-hd"
                              : selectedType === "plex"
                                ? "plex"
                                : ""
                        }
                      />
                      {popupField === "instanceName" && errors.instanceName && (
                        <div className="absolute z-10 w-full">
                          <FieldError message={errors.instanceName} />
                        </div>
                      )}
                      {blurredFields.has("instanceName") &&
                        errors.instanceName && (
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
                  <label className="text-sm text-white sm:pt-2">
                    URL<span className="text-red-500"> *</span>
                  </label>
                  <div className="flex flex-col gap-1 sm:w-80">
                    <div className="relative">
                      <input
                        type="text"
                        value={url}
                        ref={urlRef}
                        onFocus={() => setShowTestWarning(false)}
                        onBlur={() => {
                          setPopupField(null);
                          if (errors.url) {
                            setBlurredFields((prev) =>
                              new Set(prev).add("url"),
                            );
                          }
                        }}
                        onChange={(e) => {
                          setUrl(e.target.value);
                          setConnectionTested(false);
                          if (blurredFields.has("url") || errors.url) {
                            if (e.target.value.trim()) {
                              setErrors((prev) => ({ ...prev, url: null }));
                            } else {
                              setErrors((prev) => ({ ...prev, url: true }));
                            }
                          }
                        }}
                        className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("url") && errors.url ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                        placeholder={
                          selectedType === "radarr"
                            ? "http://radarr:7878"
                            : selectedType === "sonarr"
                              ? "http://sonarr:8989"
                              : selectedType === "plex"
                                ? "http://plex:32400"
                                : ""
                        }
                      />
                      {popupField === "url" && errors.url && (
                        <div className="absolute z-10 w-full">
                          <FieldError message={errors.url} />
                        </div>
                      )}
                      {blurredFields.has("url") && errors.url && (
                        <span className="mt-1 text-xs text-red-500">
                          Required
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="p-4 md:p-6">
                <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-white">
                      {selectedType === "plex" ? "Token" : "API Key"}
                    </label>
                    {selectedType === "plex" && (
                      <div className="relative flex items-center">
                        <Info
                          size={14}
                          className="text-gray-400 hover:text-white"
                          onMouseEnter={() => showToolTip("plexToken")}
                          onMouseLeave={hideTooltip}
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveTooltip(
                              activeTooltip === "plexToken"
                                ? null
                                : "plexToken",
                            );
                          }}
                        />
                        {activeTooltip === "plexToken" && (
                          <div
                            className="absolute left-full top-1/2 z-10 ml-2 mt-1 w-60 -translate-y-1/2 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-gray-300 shadow-lg sm:w-96"
                            onMouseEnter={cancelHide}
                            onMouseLeave={hideTooltip}
                          >
                            <span className="text-xs text-gray-300">
                              Please read this guide for acquiring a
                              X-Plex-Token.
                              <br />
                              <br />
                            </span>
                            <a
                              className="break-all text-blue-400"
                              href="https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
                            </a>
                          </div>
                        )}
                      </div>
                    )}
                    <span className="text-red-500"> *</span>
                  </div>
                  <div className="flex flex-col gap-1 sm:w-80">
                    <div className="relative w-full sm:w-80">
                      <input
                        type={showApiKey ? "text" : "password"}
                        ref={apiKeyRef}
                        onFocus={() => setShowTestWarning(false)}
                        onBlur={() => {
                          setPopupField(null);
                          if (errors.apiKey) {
                            setBlurredFields((prev) =>
                              new Set(prev).add("apiKey"),
                            );
                          }
                        }}
                        value={apiKey}
                        onChange={(e) => {
                          setApiKey(e.target.value);
                          setConnectionTested(false);
                          if (blurredFields.has("apiKey") || errors.apiKey) {
                            if (e.target.value.trim()) {
                              setErrors((prev) => ({ ...prev, apiKey: null }));
                            } else {
                              setErrors((prev) => ({ ...prev, apiKey: true }));
                            }
                          }
                        }}
                        className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 pr-10 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("apiKey") && errors.apiKey ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                        placeholder={
                          selectedType === "plex"
                            ? "Enter Plex token"
                            : "Enter API key"
                        }
                      />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 transition-colors hover:text-white"
                      >
                        {showApiKey ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                      {popupField === "apiKey" && errors.apiKey && (
                        <div className="absolute z-10 w-full">
                          <FieldError message={errors.apiKey} />
                        </div>
                      )}
                      {blurredFields.has("apiKey") && errors.apiKey && (
                        <span className="absolute -bottom-5 -left-0 text-xs text-red-500">
                          Required
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="absolute bottom-6 left-0 right-0 flex flex-col gap-3 border-t border-gray-700 px-4 pt-6 sm:flex-row sm:items-end sm:justify-end md:pr-6">
                {editingInstance && (
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
                          onClick={handleDeleteInstance}
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
                  onClick={handleCancelInstance}
                  disabled={isLoading}
                  className="w-full rounded-md bg-gray-700 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                >
                  {isLoading ? "Cancelling..." : "Cancel"}
                </button>
                <button
                  onClick={handleTestConnection}
                  disabled={isLoading}
                  className="w-full rounded-md bg-gray-700 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                >
                  {isLoading ? "Testing..." : "Test"}
                </button>
                <button
                  onClick={handleSaveInstance}
                  disabled={isLoading || !hasChanges}
                  className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                >
                  {isLoading
                    ? "Saving..."
                    : !hasChanges
                      ? "No Changes"
                      : "Save"}
                </button>
              </div>
              {showTestWarning && (
                <p className="absolute bottom-16 right-4 z-10 rounded-md border border-gray-800 bg-gray-950 px-3 py-1.5 text-sm text-white">
                  Test your connection before saving
                </p>
              )}
            </>
          )}
        </div>
        {/* Overlay */}
        {isSidebarOpen && (
          <div
            onClick={() => {
              setIsSidebarOpen(false);
              setShowApiKey(false);
              setErrors({});
              setBlurredFields(new Set());
              if (editingInstance) {
                setEditingInstance("");
                setSelectedType("");
                setInstanceName("");
                setUrl("");
                setApiKey("");
                setShowApiKey(false);
                setConnectionStatus(null);
                setConnectionTested(false);
                setShowTestWarning(false);
                setConfirmDelete(false);
              }
            }}
            className="fixed inset-0 z-40 bg-black bg-opacity-50"
          ></div>
        )}
      </div>
      {pendingSection && (
        <UnsavedChanges onStay={handleStay} onDiscard={handleDiscard} />
      )}
    </div>
  );
}

export default Settings;
