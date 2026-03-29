import { createPortal } from "react-dom";
import { Ellipsis, Trash2 } from "lucide-react";
function ListRow({
  type,
  item,
  selectedItem,
  onSelect,
  openPopover,
  setOpenPopover,
  popoverPos,
  setPopoverPos,
  hasChevron = false,
  onDelete,
}) {
  const isSelected =
    selectedItem?.type === item.type &&
    selectedItem?.file_hash === item.file_hash &&
    selectedItem?.instance === item.instance;
  return (
    <div className="group relative flex w-full items-center">
      <button
        onClick={() => onSelect(item)}
        key={item.file_hash}
        className={`relative z-10 w-full px-4 py-2 text-left text-sm transition-colors ${isSelected ? "text-white" : "text-gray-300 hover:text-white"}`}
      >
        <span
          className={`absolute left-0 top-0 h-full w-1 rounded-r ${isSelected ? "bg-blue-500" : "bg-transparent"}`}
        ></span>
        {item.file_name}
        {isSelected && (
          <span className="mt-0.5 block truncate text-xs text-gray-500">
            {item.source_path.split("/").slice(1, -1).join("/")}
          </span>
        )}
      </button>
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
              openPopover === `${item.type}-${item.file_hash}-${item.instance}`
                ? null
                : `${item.type}-${item.file_hash}-${item.instance}`,
            );
          }}
        >
          <Ellipsis size={18} className="cursor-default" />
        </button>
        {hasChevron && <div className="w-8" />}
        {openPopover === `${item.type}-${item.file_hash}-${item.instance}` &&
          createPortal(
            <div
              style={{
                top: popoverPos.top,
                left: popoverPos.left,
              }}
              className="fixed z-50 w-40 rounded border border-gray-700 bg-gray-900 py-1 shadow-lg duration-100"
            >
              <button
                className="w-full rounded px-4 py-2 text-left text-sm text-gray-400 hover:bg-gray-800 hover:text-white"
                onClick={(e) => {
                  e.stopPropagation();
                  fetch("/api/poster-renamer/delete-poster", {
                    method: "DELETE",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      type: type,
                      filePath: item.file_path,
                      fileName: item.file_name.trim(),
                      arrId: item.arr_id,
                      imdbId: item.imdb_id,
                      tmdbId: item.tmdb_id,
                      instance: item.instance,
                    }),
                  })
                    .then((res) => res.json())
                    .then((data) => {
                      if (data.success) {
                        setOpenPopover(null);
                        if (selectedItem?.file_path == item.file_path) {
                          onSelect(null);
                        }
                        onDelete();
                      }
                    });
                }}
              >
                <span className="flex items-center  gap-2 text-sm">
                  <Trash2 size={16} className="text-red-500" />
                  Delete Poster
                </span>
              </button>
            </div>,
            document.body,
          )}
      </div>
      <div
        className={`pointer-events-none absolute inset-0 z-0 transition-colors ${isSelected ? "bg-gray-800" : "group-hover:bg-gray-800"}`}
      />
    </div>
  );
}
export default ListRow;
