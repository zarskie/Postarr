import { useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Ellipsis, Trash2 } from "lucide-react";

function ShowRow({
  show,
  onSelect,
  selectedItem,
  openPopover,
  setOpenPopover,
  popoverPos,
  setPopoverPos,
  onDelete,
}) {
  const isSelected = selectedItem?.file_hash === show.file_hash;
  const containsSelected = show.seasons.some(
    (season) => season.file_hash === selectedItem?.file_hash,
  );
  const [manualOpen, setManualOpen] = useState(null);
  const open = manualOpen !== null ? manualOpen : containsSelected;
  const handleEllipsis = (e, hash) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setPopoverPos({ top: rect.bottom, left: rect.right - 160 });
    setOpenPopover(openPopover === hash ? null : hash);
  };

  return (
    <div>
      <div className="group relative flex w-full items-center">
        <button
          onClick={() => {
            onSelect(show);
          }}
          className={`relative z-10 flex w-full items-center justify-between px-4 py-2 text-left text-sm transition-colors ${isSelected ? "text-white" : "text-gray-300 hover:text-white"}`}
        >
          <span
            className={`absolute left-0 top-0 h-full w-1 ${isSelected ? "bg-blue-500" : "bg-transparent"}`}
          />
          <span>{show.file_name}</span>
        </button>

        <div className="flex flex-shrink-0 items-center">
          <button
            className="relative z-10 w-8 flex-shrink-0 p-2 text-sm text-gray-500 hover:text-blue-500"
            onClick={(e) => handleEllipsis(e, show.file_hash)}
          >
            <Ellipsis size={14} className="h-4 w-4" />
          </button>
          <button
            onClick={() => {
              setManualOpen(!open);
            }}
            className="relative z-10 w-8 flex-shrink-0 p-2 text-sm text-gray-300 hover:text-blue-500"
          >
            <ChevronDown
              size={16}
              className={`h-4 w-4 transition-transform ${open ? "rotate-180" : "rotate-0"}`}
            />
          </button>
        </div>

        <div
          className={`pointer-events-none absolute inset-0 z-0 transition-colors ${isSelected ? "bg-gray-800" : "group-hover:bg-gray-800"}`}
        />
      </div>
      {openPopover === show.file_hash &&
        createPortal(
          <div
            style={{
              top: popoverPos.top,
              left: popoverPos.left,
            }}
            className="animate-in fade-in zoom-in-95 fixed z-50 w-40 rounded border border-gray-700 bg-gray-900 py-1 shadow-lg duration-100"
          >
            <button
              className="w-full rounded px-4 py-2 text-left text-sm hover:bg-gray-800"
              onClick={(e) => {
                e.stopPropagation();
                fetch("/api/poster-renamer/delete-poster", {
                  method: "DELETE",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ filePath: show.file_path }),
                })
                  .then((res) => res.json())
                  .then((data) => {
                    if (data.success) {
                      setOpenPopover(null);
                      if (selectedItem.file_path == show.file_path) {
                        onSelect(null);
                      }
                      onDelete();
                    }
                  });
              }}
            >
              <span className="flex items-center  gap-2 text-sm text-white">
                <Trash2 size={16} className="text-red-500" />
                Delete Poster
              </span>
            </button>
          </div>,
          document.body,
        )}
      {open && (
        <div className="border-l-[10px] border-gray-700">
          {show.seasons.map((season) => {
            const seasonSelected = selectedItem?.file_hash === season.file_hash;
            return (
              <div
                key={season.file_hash}
                className="group relative flex w-full items-center"
              >
                <button
                  onClick={() => onSelect(season)}
                  className={`relative z-10 flex w-full items-center justify-between px-4 py-2 text-left text-sm transition-colors ${seasonSelected ? "text-white" : "text-gray-400 hover:text-white"}`}
                >
                  <span
                    className={`absolute left-0 top-0 h-full w-1 ${seasonSelected ? "bg-blue-500" : "bg-transparent"}`}
                  ></span>
                  {season.season === 0 ? "Specials" : `Season ${season.season}`}
                </button>
                <div className="flex flex-shrink-0 items-center">
                  <button
                    className="relative z-10 w-8 flex-shrink-0 p-2 text-sm text-gray-500 hover:text-blue-500"
                    onClick={(e) => handleEllipsis(e, season.file_hash)}
                  >
                    <Ellipsis size={14} className="h-4 w-4" />
                  </button>
                  <div className="w-8" />
                </div>
                {openPopover === season.file_hash &&
                  createPortal(
                    <div
                      style={{
                        top: popoverPos.top,
                        left: popoverPos.left,
                      }}
                      className="animate-in fade-in zoom-in-95 fixed z-50 w-40 rounded border border-gray-700 bg-gray-900 py-1 shadow-lg duration-100"
                    >
                      <button
                        className="w-full rounded px-4 py-2 text-left text-sm hover:bg-gray-800"
                        onClick={(e) => {
                          e.stopPropagation();
                          fetch("/api/poster-renamer/delete-poster", {
                            method: "DELETE",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              filePath: season.file_path,
                            }),
                          })
                            .then((res) => res.json())
                            .then((data) => {
                              if (data.success) {
                                setOpenPopover(null);
                                if (
                                  selectedItem.file_path == season.file_path
                                ) {
                                  onSelect(null);
                                }
                                onDelete();
                              }
                            });
                        }}
                      >
                        <span className="flex items-center  gap-2 text-sm text-white">
                          <Trash2 size={16} className="text-red-500" />
                          Delete Poster
                        </span>
                      </button>
                    </div>,
                    document.body,
                  )}
                <div
                  className={`pointer-events-none absolute inset-0 z-0 transition-colors ${seasonSelected ? "bg-gray-800" : "group-hover:bg-gray-800"}`}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
export default ShowRow;
