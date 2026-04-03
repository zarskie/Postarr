import { useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Ellipsis, ImageOff, Link } from "lucide-react";

function UnmatchedShowRow({
  type,
  show,
  openPopover,
  setOpenPopover,
  popoverPos,
  setPopoverPos,
}) {
  const [manualOpen, setManualOpen] = useState(null);
  const handleEllipsis = (e, id) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setPopoverPos({ top: rect.bottom, left: rect.right - 160 });
    setOpenPopover(openPopover === id ? null : id);
  };
  const formatSeason = (season) => {
    const num = parseInt(season.replace(/\D/g, ""), 10);
    return num === 0 ? "Specials" : `Season ${num}`;
  };
  const tmdbUrl = `https://www.themoviedb.org/tv/${show.tmdb_id}`;
  const tvdbUrl = `https://www.thetvdb.com/?tab=series&id=${show.tvdb_id}`;

  return (
    <div>
      <div className="group relative flex w-full items-center justify-between">
        <div className="relative z-10 flex flex-1 items-center gap-2 px-4 py-2">
          <div className="flex flex-col text-sm">
            <span
              className={
                show.main_poster_missing === 1
                  ? "text-gray-500"
                  : "text-gray-300"
              }
            >
              {show.title}
            </span>
            {show.main_poster_missing === 1 && (
              <span className="flex items-center gap-1 text-xs text-gray-600">
                <ImageOff size={12} />
                No series poster
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-shrink-0 items-center">
          <button
            className="relative z-10 w-8 flex-shrink-0 p-2 text-sm text-gray-500 hover:text-white"
            onClick={(e) => handleEllipsis(e, `${type}-${show.id}`)}
          >
            <Ellipsis size={18} />
          </button>
          {show.seasons.length > 0 && (
            <button
              onClick={() => {
                setManualOpen(!manualOpen);
              }}
              className="relative z-10 w-8 flex-shrink-0 p-2 text-sm text-gray-500 hover:text-white"
            >
              <ChevronDown
                size={18}
                className={`transition-transform ${manualOpen ? "rotate-180" : "rotate-0"}`}
              />
            </button>
          )}
        </div>
        <div className="pointer-events-none absolute inset-0 z-0 transition-colors group-hover:bg-gray-800" />
      </div>
      {openPopover === `${type}-${show.id}` &&
        createPortal(
          <div
            style={{
              top: popoverPos.top,
              left: popoverPos.left,
            }}
            className="fixed z-50 w-40 rounded border border-gray-700 bg-gray-900 py-1 text-gray-400 shadow-lg"
          >
            <button
              className="w-full rounded px-4 py-2 text-left text-sm hover:bg-gray-800 hover:text-white"
              onClick={(e) => {
                e.stopPropagation();
                window.open(tvdbUrl, "_blank");
                setOpenPopover(null);
              }}
            >
              <span className="flex items-center gap-2">
                <Link size={16} />
                Tvdb
              </span>
            </button>
            <button
              className="w-full rounded px-4 py-2 text-left text-sm hover:bg-gray-800 hover:text-white"
              onClick={(e) => {
                e.stopPropagation();
                window.open(tmdbUrl, "_blank");
                setOpenPopover(null);
              }}
            >
              <span className="flex items-center gap-2">
                <Link size={16} />
                Tmdb
              </span>
            </button>
          </div>,
          document.body
        )}
      {manualOpen && (
        <div className="border-l-[10px] border-gray-700">
          {show.seasons.map((season) => (
            <div
              className="group relative flex w-full items-center"
              key={season.id}
            >
              <span className="relative z-10 flex-1 px-4 py-2 text-sm text-gray-400">
                {formatSeason(season.season)}
              </span>
              <div className="pointer-events-none absolute inset-0 z-0 transition-colors group-hover:bg-gray-800" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
export default UnmatchedShowRow;
