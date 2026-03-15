import { X } from "lucide-react";
import { useEffect } from "react";

function UnsavedChanges({ onStay, onDiscard }) {
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={onStay}
    >
      <div
        className="flex h-full w-full flex-col bg-gray-800 shadow-2xl sm:h-auto sm:w-auto sm:min-w-[680px] sm:rounded-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-600 py-4">
          <h2 className="px-6 text-lg font-medium text-white">
            Unsaved Changes
          </h2>
          <button
            onClick={onStay}
            className="rounded-md px-4 text-gray-400 transition-colors hover:text-white"
          >
            <X size={20} />
          </button>
        </div>
        <div className="flex-1 border-b border-gray-600 px-6 py-6 sm:flex-none">
          <p className="text-sm text-gray-400">
            You have unsaved changes. Are you sure you want to leave this page?
          </p>
        </div>
        <div className="flex flex-col items-center gap-3 px-4 py-4 sm:flex-row sm:justify-end">
          <button
            onClick={onStay}
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 sm:w-auto"
          >
            Stay and review changes
          </button>
          <button
            onClick={onDiscard}
            className="w-full rounded-md bg-gray-600 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-500 sm:w-auto"
          >
            Discard changes and leave
          </button>
        </div>
      </div>
    </div>
  );
}
export default UnsavedChanges;
