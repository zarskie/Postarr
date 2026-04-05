import { useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Ellipsis, Trash2, ImageOff } from "lucide-react";

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
  const isSelected =
    selectedItem?.arr_id === show.arr_id &&
    selectedItem?.instance === show.instance;
  const containsSelected = show.seasons.some(
    (season) => season.file_hash === selectedItem?.file_hash
  );
  const [manualOpen, setManualOpen] = useState(null);
  const open = manualOpen !== null ? manualOpen : containsSelected;
  const handleEllipsis = (e, hash) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setPopoverPos({ top: rect.bottom, left: rect.right - 160 });
    setOpenPopover(openPopover === hash ? null : hash);
  };
  const mainPosterMissing = !show.file_path;

  return (
    <div>
      <div className="group relative flex w-full items-center">
        <button
          onClick={() => {
            onSelect(show);
          }}
          className={`relative z-10 flex w-full items-center justify-between px-4 py-2 text-left text-sm transition-colors ${isSelected ? "text-white" : "text-gray-300 hover:text-white"}`}
        >
          <div className="flex flex-col">
            <span
              className={`absolute left-0 top-0 h-full w-1 rounded-r ${isSelected ? "bg-blue-500" : "bg-transparent"}`}
            />
            <span className={mainPosterMissing ? "text-gray-500" : ""}>
              {show.file_name}
            </span>
            {mainPosterMissing && (
              <span className="flex items-center gap-1 text-xs text-gray-600">
                <ImageOff size={12} />
                No poster
              </span>
            )}
            {isSelected && (
              <span className="mt-0.5 block truncate text-xs text-gray-500">
                {show.source_path.split("/").slice(1, -1).join("/")}
              </span>
            )}
          </div>
        </button>

        <div className="flex flex-shrink-0 items-center">
          {!mainPosterMissing && (
            <button
              className="relative z-10 w-8 flex-shrink-0 p-2 text-sm text-gray-500 hover:text-white"
              onClick={(e) =>
                handleEllipsis(e, `show-${show.arr_id}-${show.instance}`)
              }
            >
              <Ellipsis size={18} className="cursor-default" />
            </button>
          )}
          {show.seasons.length > 0 && (
            <button
              onClick={() => {
                setManualOpen(!open);
              }}
              className="relative z-10 w-8 flex-shrink-0 p-2 text-sm text-gray-500 hover:text-white"
            >
              <ChevronDown
                size={18}
                className={`cursor-default transition-transform ${open ? "rotate-180" : "rotate-0"}`}
              />
            </button>
          )}
        </div>

        <div
          className={`pointer-events-none absolute inset-0 z-0 transition-colors ${isSelected ? "bg-gray-800" : "group-hover:bg-gray-800"}`}
        />
      </div>
      {openPopover === `show-${show.arr_id}-${show.instance}` &&
        createPortal(
          <div
            style={{
              top: popoverPos.top,
              left: popoverPos.left,
            }}
            className="fixed z-50 w-40 rounded border border-gray-700 bg-gray-900 py-1 shadow-lg"
          >
            <button
              className="w-full rounded px-4 py-2 text-left text-sm text-gray-400 hover:bg-gray-800 hover:text-white"
              onClick={(e) => {
                e.stopPropagation();
                fetch("/api/poster-renamer/delete-poster", {
                  method: "DELETE",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    filePath: show.file_path,
                    type: "show",
                    fileName: show.file_name.trim(),
                    arrId: show.arr_id,
                    instance: show.instance,
                    imdbId: show.imdb_id,
                    tmdbId: show.tmdb_id,
                    tvdbId: show.tvdb_id,
                    mainPosterMissing: true,
                  }),
                })
                  .then((res) => res.json())
                  .then((data) => {
                    if (data.success) {
                      setOpenPopover(null);
                      if (selectedItem?.file_path == show.file_path) {
                        onSelect(null);
                      }
                      onDelete();
                    }
                  });
              }}
            >
              <span className="flex items-center gap-2">
                <Trash2 size={16} className="text-red-500" />
                Delete Poster
              </span>
            </button>
          </div>,
          document.body
        )}
      {open && (
        <div className="border-l-[10px] border-gray-700">
          {show.seasons.map((season) => {
            const seasonSelected = selectedItem?.file_path === season.file_path;
            return (
              <div
                key={season.file_path}
                className="group relative flex w-full items-center"
              >
                <button
                  onClick={() => onSelect(season)}
                  className={`relative z-10 flex w-full items-center justify-between px-4 py-2 text-left text-sm transition-colors ${seasonSelected ? "text-white" : "text-gray-400 hover:text-white"}`}
                >
                  <div className="flex flex-col">
                    <span
                      className={`absolute left-0 top-0 h-full w-1 rounded-r ${seasonSelected ? "bg-blue-500" : "bg-transparent"}`}
                    ></span>
                    {season.season === 0
                      ? "Specials"
                      : `Season ${season.season}`}
                    {seasonSelected && (
                      <span className="block truncate text-xs text-gray-500">
                        {season.source_path.split("/").slice(1, -1).join("/")}
                      </span>
                    )}
                  </div>
                </button>
                <div className="flex flex-shrink-0 items-center">
                  <button
                    className="relative z-10 w-8 flex-shrink-0 p-2 text-sm text-gray-500 hover:text-white"
                    onClick={(e) => handleEllipsis(e, season.file_path)}
                  >
                    <Ellipsis size={18} className="cursor-default" />
                  </button>
                  <div className="w-8" />
                </div>
                {openPopover === season.file_path &&
                  createPortal(
                    <div
                      style={{
                        top: popoverPos.top,
                        left: popoverPos.left,
                      }}
                      className="fixed z-50 w-40 rounded border border-gray-700 bg-gray-900 py-1 shadow-lg"
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
                              type: "season",
                              fileName: show.file_name.trim(),
                              arrId: show.arr_id,
                              instance: show.instance,
                              imdbId: show.imdb_id,
                              tmdbId: show.tmdb_id,
                              tvdbId: show.tvdb_id,
                              mainPosterMissing: false,
                              seasonNumber: season.season,
                            }),
                          })
                            .then((res) => res.json())
                            .then((data) => {
                              if (data.success) {
                                setOpenPopover(null);
                                if (
                                  selectedItem?.file_path == season.file_path
                                ) {
                                  onSelect(null);
                                }
                                onDelete();
                              }
                            });
                        }}
                      >
                        <span className="flex items-center gap-2 text-sm text-white">
                          <Trash2 size={16} className="text-red-500" />
                          Delete Poster
                        </span>
                      </button>
                    </div>,
                    document.body
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
