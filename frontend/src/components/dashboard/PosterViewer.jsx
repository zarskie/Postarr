import { useEffect, useState } from "react";
import ShowRow from "../utils/ShowRow";
import ListRow from "../utils/ListRow";
import { usePoster } from "../../context/PosterContext";
import { useUnmatched } from "../../context/UnmatchedContext";

function PosterViewer() {
  const [popoverPos, setPopoverPos] = useState({ top: 0, left: 0 });
  const [activeFilter, setActiveFilter] = useState("all");
  const [searchValue, setSearchValue] = useState("");
  const { filePaths, refreshFilePaths } = usePoster();
  const { refreshUnmatchedData } = useUnmatched();
  const [selectedItem, setSelectedItem] = useState(null);
  const [openPopover, setOpenPopover] = useState(null);
  const filters = [
    { id: "all", label: "All" },
    { id: "movies", label: "Movies" },
    { id: "shows", label: "Series" },
    { id: "collections", label: "Collections" },
  ];
  const search = searchValue.toLowerCase();
  const filteredMovies = filePaths.movies.filter((movie) =>
    movie.file_name.toLowerCase().includes(search),
  );
  const filteredCollections = filePaths.collections.filter((collection) =>
    collection.file_name.toLowerCase().includes(search),
  );
  const filteredShows = Object.values(filePaths.shows).filter((show) =>
    show.file_name.toLowerCase().includes(search),
  );
  const allItems = [
    ...filePaths.movies.map((item) => ({ ...item, type: "movie" })),
    ...filePaths.collections.map((item) => ({ ...item, type: "collection" })),
    ...Object.values(filePaths.shows).map((item) => ({
      ...item,
      type: "show",
    })),
  ];
  const filteredItems = allItems
    .filter((item) => item.file_name.toLowerCase().includes(search))
    .sort((a, b) => a.file_name.localeCompare(b.file_name));

  useEffect(() => {
    const handler = () => setOpenPopover(null);
    document.addEventListener("click", handler);
    document.addEventListener("scroll", handler, true);
    return () => {
      document.removeEventListener("click", handler);
      document.removeEventListener("scroll", handler, true);
    };
  }, []);

  return (
    <>
      <div className="flex flex-col">
        <div className="flex flex-col overflow-hidden rounded border border-gray-700 bg-gray-900 lg:flex-row">
          <div className="flex max-h-[550px] w-full flex-col border-b border-gray-700  bg-gray-900 lg:max-h-[650px] lg:w-1/2 lg:border-b-0 lg:border-r">
            <nav className="mb-2 flex-shrink-0 border-b border-gray-700 bg-gray-900">
              <ul className="flex text-sm font-medium">
                {filters.map((filter) => {
                  const isActive = activeFilter === filter.id;
                  return (
                    <li key={filter.id} className="flex-1">
                      <button
                        onClick={() => {
                          setActiveFilter(filter.id);
                        }}
                        className={`relative flex w-full items-center justify-center gap-3 px-4 py-3 transition-colors ${activeFilter === filter.id ? "bg-gray-700 text-white" : "text-gray-400 hover:bg-gray-700 hover:text-white"}`}
                      >
                        <span
                          className={`absolute bottom-0 left-0 h-1 w-full rounded-t ${isActive ? "bg-blue-500" : "bg-transparent"}`}
                        />
                        <span className="flex-1">{filter.label}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </nav>
            <div className="mb-2 flex-shrink-0 bg-gray-900 p-2">
              <input
                type="text"
                value={searchValue}
                onChange={(e) => {
                  setSearchValue(e.target.value);
                }}
                className="w-full rounded border border-gray-700 bg-gray-800 px-4 py-2 text-sm  text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Search assets..."
              />
            </div>
            <div className="flex min-h-0 flex-1 flex-col pb-2">
              <div className="flex flex-1 flex-col overflow-y-auto">
                {activeFilter === "all" &&
                  filteredItems.map((item) => {
                    if (item.type === "show")
                      return (
                        <ShowRow
                          key={item.arr_id}
                          type={item.type}
                          show={item}
                          onSelect={setSelectedItem}
                          selectedItem={selectedItem}
                          openPopover={openPopover}
                          setOpenPopover={setOpenPopover}
                          popoverPos={popoverPos}
                          setPopoverPos={setPopoverPos}
                          hasChevron={true}
                          onDelete={() => {
                            refreshFilePaths();
                            refreshUnmatchedData();
                          }}
                        />
                      );
                    return (
                      <ListRow
                        key={item.file_hash}
                        type={item.type}
                        item={item}
                        selectedItem={selectedItem}
                        onSelect={setSelectedItem}
                        openPopover={openPopover}
                        setOpenPopover={setOpenPopover}
                        popoverPos={popoverPos}
                        setPopoverPos={setPopoverPos}
                        hasChevron={false}
                        onDelete={() => {
                          refreshFilePaths();
                          refreshUnmatchedData();
                        }}
                      />
                    );
                  })}
                {activeFilter === "movies" &&
                  filteredMovies.map((movie) => (
                    <ListRow
                      key={movie.file_hash}
                      type="movie"
                      item={movie}
                      selectedItem={selectedItem}
                      onSelect={setSelectedItem}
                      openPopover={openPopover}
                      setOpenPopover={setOpenPopover}
                      popoverPos={popoverPos}
                      setPopoverPos={setPopoverPos}
                      onDelete={() => {
                        refreshFilePaths();
                        refreshUnmatchedData();
                      }}
                    />
                  ))}
                {activeFilter === "shows" &&
                  filteredShows.map((show) => (
                    <ShowRow
                      key={show.arr_id}
                      type="show"
                      show={show}
                      onSelect={setSelectedItem}
                      selectedItem={selectedItem}
                      openPopover={openPopover}
                      setOpenPopover={setOpenPopover}
                      popoverPos={popoverPos}
                      setPopoverPos={setPopoverPos}
                      onDelete={() => {
                        refreshFilePaths();
                        refreshUnmatchedData();
                      }}
                    />
                  ))}
                {activeFilter === "collections" &&
                  filteredCollections.map((collection) => (
                    <ListRow
                      key={collection.file_hash}
                      type="collection"
                      item={collection}
                      selectedItem={selectedItem}
                      onSelect={setSelectedItem}
                      openPopover={openPopover}
                      setOpenPopover={setOpenPopover}
                      popoverPos={popoverPos}
                      setPopoverPos={setPopoverPos}
                      onDelete={() => {
                        refreshFilePaths();
                        refreshUnmatchedData();
                      }}
                    />
                  ))}
              </div>
            </div>
          </div>
          <div className="flex min-h-[550px] w-full items-center justify-center overflow-hidden border-gray-700 bg-gray-900 p-6 lg:max-h-[650px] lg:w-1/2 lg:border-b-0 lg:border-r">
            {selectedItem ? (
              selectedItem.file_path ? (
                <img
                  key={selectedItem.file_path}
                  src={`/api/poster-renamer${selectedItem.file_path}`}
                  alt={selectedItem.file_name}
                  className="h-full max-h-[600px] w-full rounded object-contain text-gray-300 duration-300 animate-in fade-in lg:max-h-full"
                />
              ) : (
                <span className="text-sm text-gray-500">No poster found</span>
              )
            ) : (
              <span className="text-sm text-gray-500">
                Select an asset to preview
              </span>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
export default PosterViewer;
