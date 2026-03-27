import { createPortal } from "react-dom";
import { Ellipsis, Link } from "lucide-react";
function UnmatchedRow({
  type,
  item,
  openPopover,
  setOpenPopover,
  popoverPos,
  setPopoverPos,
}) {
  const tmdbUrl = `https://www.themoviedb.org/movie/${item.tmdb_id}`;
  return (
    <div className="group relative flex w-full items-center justify-between">
      <span className="relative z-10 flex-1 px-4 py-2 text-sm text-gray-300 hover:text-white">
        {item.title}
      </span>
      {type === "movie" && (
        <div className="flex flex-shrink-0 items-center">
          <button
            className="relative z-10 p-2 text-sm text-gray-500 hover:text-white"
            onClick={(e) => {
              e.stopPropagation();
              const rect = e.currentTarget.getBoundingClientRect();
              setPopoverPos({
                top: rect.bottom,
                left: rect.right - 160,
              });
              setOpenPopover(
                openPopover === `${type}-${item.id}`
                  ? null
                  : `${type}-${item.id}`,
              );
            }}
          >
            <Ellipsis size={18} />
          </button>
          {openPopover === `${type}-${item.id}` &&
            createPortal(
              <div
                style={{
                  top: popoverPos.top,
                  left: popoverPos.left,
                }}
                className="fixed z-50 w-40 rounded border border-gray-700 bg-gray-900 py-1 text-gray-400 shadow-lg duration-100"
              >
                <button
                  className="w-full rounded px-4 py-2 text-left text-sm hover:bg-gray-800 hover:text-white"
                  onClick={(e) => {
                    e.stopPropagation();
                    window.open(tmdbUrl, "_blank");
                    setOpenPopover(null);
                  }}
                >
                  <span className="flex items-center  gap-2 text-sm">
                    <Link size={16} />
                    Tmdb
                  </span>
                </button>
              </div>,
              document.body,
            )}
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 z-0 transition-colors group-hover:bg-gray-800" />
    </div>
  );
}
export default UnmatchedRow;
