import { X, ChevronDown, Check } from "lucide-react";
import FieldError from "../../components/common/FieldError";
import { useState, useEffect, useRef, useMemo } from "react";

function NotifierSidebar({ isOpen, editingNotifier, onClose, onSave }) {
  const urlRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);
  const [notifierType, setNotifierType] = useState(editingNotifier?.type || "");
  const [url, setUrl] = useState(editingNotifier?.url || "");
  const [notifierEnabled, setNotifierEnabled] = useState(
    editingNotifier?.enabled || false
  );
  const [errors, setErrors] = useState({});
  const [popupField, setPopupField] = useState(null);
  const [blurredFields, setBlurredFields] = useState(new Set());
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [notifierInitialState, setNotifierInitialState] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setNotifierType(editingNotifier?.type || "");
      setUrl(editingNotifier?.url || "");
      setErrors({});
      setConfirmDelete(false);
      setNotifierInitialState(
        editingNotifier?.id
          ? {
              notifierType: editingNotifier.type,
              url: editingNotifier.url,
              notifierEnabled: editingNotifier.enabled,
            }
          : null
      );
      setNotifierEnabled(editingNotifier?.enabled ?? true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const handleCancel = () => {
    setErrors({});
    setPopupField(null);
    setBlurredFields(new Set());
    setConfirmDelete(false);
    onClose();
  };

  const handleDeleteNotifier = async () => {
    if (!editingNotifier) return;
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch("/api/settings/delete-notifier", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: editingNotifier.id }),
      });
      const result = await response.json();
      if (response.ok) {
        onSave();
        onClose();
      } else {
        console.error("Error deleting notifier:", result.message);
      }
    } catch (error) {
      console.error("Error deleting notifier:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveNotifier = async () => {
    const newErrors = {};
    if (!url) newErrors.url = true;
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setPopupField("url");
      urlRef.current?.focus();
      return;
    }
    setIsLoading(true);
    try {
      const endpoint = editingNotifier?.id
        ? "/api/settings/update-notifier"
        : "/api/settings/add-notifier";
      const body = editingNotifier?.id
        ? {
            id: editingNotifier.id,
            type: notifierType,
            url,
            enabled: notifierEnabled,
          }
        : { type: notifierType, url };
      const response = await fetch(endpoint, {
        method: editingNotifier?.id ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (response.ok) {
        onSave();
        setNotifierInitialState({
          notifierType: notifierType,
          url: url.trim(),
        });
        onClose();
      } else {
        setErrors({ url: result.message });
      }
    } catch (error) {
      console.error("Error saving notifier:", error);
    } finally {
      setIsLoading(false);
    }
  };
  const handleTestWebhook = async () => {
    const newErrors = {};
    if (!url) newErrors.url = true;
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setPopupField("url");
      urlRef.current?.focus();
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch("/api/settings/test-notifier", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, type: notifierType }),
      });
      const result = await response.json();
      if (response.ok) {
        setConnectionStatus({
          success: true,
          message: result.message || "Connection Successful!",
        });
      } else {
        setConnectionStatus({
          success: false,
          message: result.message || "Connection Failed!",
        });
        console.error("Test failed:", result.message);
      }
    } catch (error) {
      setConnectionStatus({
        success: false,
        message: "Network error",
      });
      console.error("Test failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const hasChanges = useMemo(() => {
    if (editingNotifier) {
      if (!notifierInitialState) return true;
      return (
        notifierType !== notifierInitialState.notifierType ||
        url !== notifierInitialState.url ||
        notifierEnabled !== notifierInitialState.notifierEnabled
      );
    }
    return true;
  }, [
    notifierInitialState,
    editingNotifier,
    notifierType,
    url,
    notifierEnabled,
  ]);

  useEffect(() => {
    if (connectionStatus) {
      const timer = setTimeout(() => {
        setConnectionStatus(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [connectionStatus]);

  return (
    <>
      <div className="pointer-events-none fixed right-4 top-4 z-[65] flex flex-col gap-2">
        {connectionStatus && (
          <div
            className={`flex transform items-center gap-3 rounded-lg border px-4 py-3 shadow-2xl transition-all duration-500 ease-in-out animate-in fade-in slide-in-from-right-10 ${connectionStatus.success ? "border-green-500 bg-gray-800 text-green-400" : "border-red-500 bg-gray-800 text-red-400"}`}
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
      <div
        className={`fixed right-0 top-0 z-[60] h-full w-full transform bg-gray-900 shadow-2xl transition-transform duration-300 ease-in-out sm:max-w-xl ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-start justify-between bg-gray-700 p-6">
          <div className="flex flex-col gap-2">
            <h3 className="text-xl font-semibold text-white">
              {editingNotifier?.id ? "Edit Notifier" : "Add Notifier"}
            </h3>
            <p className="text-sm text-white">
              {editingNotifier?.id ? "Edit Notifier." : "Add Notifier."}
            </p>
          </div>
          <button
            onClick={handleCancel}
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
                value={notifierType}
                disabled={!!editingNotifier?.id}
                onChange={(e) => {
                  setNotifierType(e.target.value);
                  setUrl("");
                  setErrors({});
                }}
                className="w-full cursor-pointer appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">Select type</option>
                <option value="discord">Discord</option>
              </select>
              <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                <ChevronDown size={18} />
              </div>
            </div>
          </div>
        </div>
        {notifierType && (
          <>
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
                      onBlur={() => {
                        setPopupField(null);
                        if (errors.url) {
                          setBlurredFields((prev) => new Set(prev).add("url"));
                        }
                      }}
                      onChange={(e) => {
                        setUrl(e.target.value);
                        if (blurredFields.has("url") || errors.url) {
                          if (e.target.value.trim()) {
                            setErrors((prev) => ({ ...prev, url: null }));
                          } else {
                            setErrors((prev) => ({ ...prev, url: true }));
                          }
                        }
                      }}
                      className={`w-full rounded-md border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 ${blurredFields.has("url") && errors.url ? "border-red-500 focus:ring-red-500" : "border-gray-600 focus:ring-blue-500"}`}
                      placeholder={"https://discord.com/api/webhooks/000/xxx"}
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
            {editingNotifier?.id && (
              <div className="p-4 md:p-6">
                <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <label className="text-sm text-white">Enabled</label>
                  <div className="sm:w-80">
                    <label className="flex cursor-pointer items-center gap-3">
                      <input
                        type="checkbox"
                        checked={notifierEnabled}
                        onChange={(e) => setNotifierEnabled(e.target.checked)}
                        className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-offset-0"
                      />
                      <span className="text-sm text-gray-400">
                        {notifierEnabled
                          ? "Notifier is enabled"
                          : "Notifier is disabled"}
                      </span>
                    </label>
                  </div>
                </div>
              </div>
            )}
            <div className="absolute bottom-6 left-0 right-0 flex flex-col gap-3 border-t border-gray-700 px-4 pt-6 sm:flex-row sm:items-end sm:justify-end md:pr-6">
              {editingNotifier?.id && (
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
                        onClick={handleDeleteNotifier}
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
                onClick={handleTestWebhook}
                disabled={isLoading}
                className="w-full rounded-md bg-gray-700 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
              >
                {isLoading ? "Testing..." : "Test"}
              </button>
              <button
                onClick={handleSaveNotifier}
                disabled={isLoading || !hasChanges}
                className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
              >
                {isLoading ? "Saving..." : !hasChanges ? "No Changes" : "Save"}
              </button>
            </div>
          </>
        )}
      </div>
      {/* Overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-[55] bg-black bg-opacity-50"
        />
      )}
    </>
  );
}

export default NotifierSidebar;
