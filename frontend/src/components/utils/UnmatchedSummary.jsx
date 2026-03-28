import { useState } from "react";
import { ChevronDown } from "lucide-react";

function UnmatchedSummary({
  type,
  missingCount,
  totalCount,
  percentComplete,
  onMissingClick,
  showAllUnmatched,
}) {
  const percent = parseFloat(percentComplete);
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="flex w-full flex-col self-start rounded-lg border border-gray-700 bg-gray-900">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex cursor-default items-center justify-between p-4"
      >
        <span className="text-sm font-medium capitalize text-white">
          {type}
        </span>

        <div className="flex items-center gap-2">
          <span
            className="cursor-pointer rounded-full border border-blue-500 bg-blue-700 px-2 py-1 text-xs text-white hover:bg-blue-600"
            onClick={(e) => {
              e.stopPropagation();
              onMissingClick?.(type);
            }}
          >
            {missingCount} missing
          </span>
          <ChevronDown
            size={16}
            className={`text-gray-400 transition-transform ${isOpen ? "rotate-180" : "rotate-0"}`}
          />
        </div>
      </button>
      <div
        className={`overflow-hidden transition-all duration-300 ${isOpen ? "max-h-64" : "max-h-0"}`}
      >
        <div className="flex flex-col gap-4 border-t border-gray-800 p-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
            <span className="text-sm text-gray-400">Total</span>
            <span className="text-sm text-white">{totalCount}</span>
          </div>
          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
            <span className="text-sm text-gray-400">With Posters</span>
            <span className="text-sm text-white">
              {totalCount - missingCount}
            </span>
          </div>
          <div className="flex flex-col items-center justify-center gap-2">
            <div className="h-1.5 w-full rounded-full bg-gray-700">
              <div
                className="h-1.5 rounded-full bg-blue-500 transition-all duration-300"
                style={{
                  width: `${percent}%`,
                  background: "linear-gradient(to right, #3b82f6, #8b5cf6)",
                }}
              />
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400">{percentComplete}</span>
              <span className="text-xs text-gray-400">Complete</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
export default UnmatchedSummary;
