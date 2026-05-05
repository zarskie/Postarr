import { useState, useMemo, useEffect } from "react";
import { X, ChevronDown } from "lucide-react";

function NotifierEventSidebar({ isOpen, onClose }) {
  const [selectedModule, setSelectedModule] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [eventsInitialState, setEventsInitialState] = useState(null);
  const [runStart, setRunStart] = useState(false);
  const [runEnd, setRunEnd] = useState(false);
  const [runError, setRunError] = useState(false);
  const [renameSummary, setRenameSummary] = useState(false);
  const [uploadSummary, setUploadSummary] = useState(false);
  const [webhookItemNotFound, setWebhookItemNotFound] = useState(false);

  const handleSaveEvents = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/settings/save-notifier-events", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          module: selectedModule,
          events: [
            ...(runStart ? ["run_start"] : []),
            ...(runEnd ? ["run_end"] : []),
            ...(runError ? ["run_error"] : []),
            ...(selectedModule === "Poster Renamerr" && renameSummary
              ? ["rename_summary"]
              : []),
            ...(selectedModule === "Plex Uploaderr" && uploadSummary
              ? ["upload_summary"]
              : []),
            ...(selectedModule === "Plex Uploaderr" && webhookItemNotFound
              ? ["webhook_item_not_found"]
              : []),
          ],
        }),
      });
      if (response.ok) {
        onClose();
      }
    } catch (error) {
      console.error("Error saving notifier events:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setSelectedModule("");
    onClose();
  };
  const hasChanges = useMemo(() => {
    if (!eventsInitialState) return true;
    return (
      runStart !== eventsInitialState.runStart ||
      runEnd !== eventsInitialState.runEnd ||
      runError !== eventsInitialState.runError ||
      renameSummary !== eventsInitialState.renameSummary ||
      uploadSummary !== eventsInitialState.uploadSummary ||
      webhookItemNotFound !== eventsInitialState.webhookItemNotFound
    );
  }, [
    eventsInitialState,
    runEnd,
    runStart,
    runError,
    renameSummary,
    uploadSummary,
    webhookItemNotFound,
  ]);

  useEffect(() => {
    if (!selectedModule) return;
    const fetchEvents = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(
          `/api/settings/notifier-events?module=${encodeURIComponent(selectedModule)}`
        );
        const result = await response.json();
        if (response.ok) {
          const events = result.events || [];
          const rs = events.includes("run_start");
          const re = events.includes("run_end");
          const rer = events.includes("run_error");
          setRunStart(rs);
          setRunEnd(re);
          setRunError(rer);
          setRenameSummary(events.includes("rename_summary"));
          setUploadSummary(events.includes("upload_summary"));
          setWebhookItemNotFound(events.includes("webhook_item_not_found"));
          setEventsInitialState({
            runStart: rs,
            runEnd: re,
            runError: rer,
            renameSummary: events.includes("rename_summary"),
            uploadSummary: events.includes("upload_summary"),
            webhookItemNotFound: events.includes("webhook_item_not_found"),
          });
        }
      } catch (error) {
        console.error("Error fetching notifier events", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchEvents();
  }, [selectedModule]);

  return (
    <>
      <div
        className={`fixed right-0 top-0 z-[60] h-full w-full transform bg-gray-900 shadow-2xl transition-transform duration-300 ease-in-out sm:max-w-xl ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-start justify-between bg-gray-700 p-6">
          <div className="flex flex-col gap-2">
            <h3 className="text-xl font-semibold text-white">
              Configure Events
            </h3>
            <p className="text-sm text-white">Configure Notification Events.</p>
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
            <label className="text-sm text-white sm:pt-2">Module</label>
            <div className="relative sm:w-80">
              <select
                value={selectedModule}
                onChange={(e) => {
                  setSelectedModule(e.target.value);
                  setRunStart(false);
                  setRunEnd(false);
                  setRunError(false);
                  setRenameSummary(false);
                  setUploadSummary(false);
                  setWebhookItemNotFound(false);
                  setEventsInitialState(null);
                }}
                className="w-full cursor-pointer appearance-none rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">Select Module</option>
                <option value="Poster Renamerr">Poster Renamerr</option>
                <option value="Plex Uploaderr">Plex Uploaderr</option>
                <option value="Unmatched Assets">Unmatched Assets</option>
                <option value="Drive Sync">Drive Sync</option>
              </select>
              <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                <ChevronDown size={18} />
              </div>
            </div>
          </div>
        </div>
        {selectedModule && (
          <>
            <div className="flex flex-col gap-4 p-4 md:p-6">
              <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <label className="text-sm text-white">Run Start</label>
                <div className="sm:w-80">
                  <label className="flex cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={runStart}
                      onChange={(e) => setRunStart(e.target.checked)}
                      className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-offset-0"
                    />
                    <span className="text-sm text-gray-400">
                      Notify on run start
                    </span>
                  </label>
                </div>
              </div>
              <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <label className="text-sm text-white">Run End</label>
                <div className="sm:w-80">
                  <label className="flex cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={runEnd}
                      onChange={(e) => setRunEnd(e.target.checked)}
                      className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-offset-0"
                    />
                    <span className="text-sm text-gray-400">
                      Notify on run end
                    </span>
                  </label>
                </div>
              </div>
              <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <label className="text-sm text-white">Errors</label>
                <div className="sm:w-80">
                  <label className="flex cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={runError}
                      onChange={(e) => setRunError(e.target.checked)}
                      className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-offset-0"
                    />
                    <span className="text-sm text-gray-400">
                      Notify on run error
                    </span>
                  </label>
                </div>
              </div>
              {selectedModule === "Poster Renamerr" && (
                <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <label className="text-sm text-white">Rename Summary</label>
                  <div className="sm:w-80">
                    <label className="flex cursor-pointer items-center gap-3">
                      <input
                        type="checkbox"
                        checked={renameSummary}
                        onChange={(e) => setRenameSummary(e.target.checked)}
                        className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-offset-0"
                      />
                      <span className="text-sm text-gray-400">
                        Notify rename summary
                      </span>
                    </label>
                  </div>
                </div>
              )}
              {selectedModule === "Plex Uploaderr" && (
                <>
                  <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <label className="text-sm text-white">Upload Summary</label>
                    <div className="sm:w-80">
                      <label className="flex cursor-pointer items-center gap-3">
                        <input
                          type="checkbox"
                          checked={uploadSummary}
                          onChange={(e) => setUploadSummary(e.target.checked)}
                          className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-offset-0"
                        />
                        <span className="text-sm text-gray-400">
                          Notify upload summary
                        </span>
                      </label>
                    </div>
                  </div>
                  <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <label className="text-sm text-white">
                      Webhook Item Not Found
                    </label>
                    <div className="sm:w-80">
                      <label className="flex cursor-pointer items-center gap-3">
                        <input
                          type="checkbox"
                          checked={webhookItemNotFound}
                          onChange={(e) =>
                            setWebhookItemNotFound(e.target.checked)
                          }
                          className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-offset-0"
                        />
                        <span className="text-sm text-gray-400">
                          Notify webhook item not found
                        </span>
                      </label>
                    </div>
                  </div>
                </>
              )}
            </div>
            <div className="absolute bottom-6 left-0 right-0 flex flex-col gap-3 border-t border-gray-700 px-4 pt-6 sm:flex-row sm:items-end sm:justify-end md:pr-6">
              <button
                onClick={handleCancel}
                disabled={isLoading}
                className="w-full rounded-md bg-gray-700 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
              >
                {isLoading ? "Cancelling..." : "Cancel"}
              </button>
              <button
                onClick={handleSaveEvents}
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
          onClick={handleCancel}
          className="fixed inset-0 z-[55] bg-black bg-opacity-50"
        />
      )}
    </>
  );
}
export default NotifierEventSidebar;
