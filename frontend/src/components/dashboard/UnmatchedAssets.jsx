import { useState, useEffect } from "react";
import UnmatchedRow from "../utils/UnmatchedRow";
import UnmatchedShowRow from "../utils/UnmatchedShowRow";
import { useUnmatched } from "../../context/UnmatchedContext";

function UnmatchedAssets({ activeFilter: initialFilter = "all" }) {
  const { unmatchedData } = useUnmatched();
  const [searchValue, setSearchValue] = useState("");
  const [activeFilter, setActiveFilter] = useState(initialFilter);
  const [popoverPos, setPopoverPos] = useState({ top: 0, left: 0 });
  const [openPopover, setOpenPopover] = useState(null);
  const filters = [
    { id: "all", label: "All" },
    { id: "movies", label: "Movies" },
    { id: "shows", label: "Series" },
    { id: "collections", label: "Collections" },
  ];
  const search = searchValue.toLowerCase();
  const filteredMovies = unmatchedData.unmatchedMedia.movies.filter((movie) =>
    movie.title.toLowerCase().includes(search),
  );
  const filteredCollections = unmatchedData.unmatchedMedia.collections.filter(
    (collection) => collection.title.toLowerCase().includes(search),
  );
  const filteredShows = unmatchedData.unmatchedMedia.shows.filter((show) =>
    show.title.toLowerCase().includes(search),
  );
  const allItems = [
    ...unmatchedData.unmatchedMedia.movies.map((item) => ({
      ...item,
      type: "movie",
    })),
    ...unmatchedData.unmatchedMedia.collections.map((item) => ({
      ...item,
      type: "collection",
    })),
    ...unmatchedData.unmatchedMedia.shows.map((item) => ({
      ...item,
      type: "show",
    })),
  ];
  const filteredItems = allItems
    .filter((item) => item.title.toLowerCase().includes(search))
    .sort((a, b) => a.title.localeCompare(b.title));

  useEffect(() => {
    const handler = () => setOpenPopover(null);
    document.addEventListener("click", handler);
    document.addEventListener("scroll", handler, true);
    return () => {
      document.removeEventListener("click", handler);
      document.removeEventListener("scroll", handler, true);
    };
  }, []);

  useEffect(() => {
    setActiveFilter(initialFilter);
  }, [initialFilter]);
  return (
    <>
      <div className="flex flex-col">
        <div className="flex max-h-[550px] w-full flex-col overflow-hidden rounded border border-gray-700  bg-gray-900 md:w-1/2 lg:max-h-[650px]">
          <nav className="mb-2 flex-shrink-0 border-b border-gray-700 bg-gray-900">
            <ul className="flex text-sm font-medium">
              {filters.map((filter) => {
                if (
                  unmatchedData.disableCollections &&
                  filter.id === "collections"
                ) {
                  return null;
                }
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
              placeholder="Search missing..."
            />
          </div>
          <div className="flex min-h-0 flex-1 flex-col pb-2">
            <div className="flex flex-1 flex-col overflow-y-auto">
              {activeFilter === "all" &&
                filteredItems.map((item) => {
                  if (item.type === "show") {
                    return (
                      <UnmatchedShowRow
                        type={item.type}
                        key={`${item.type}-${item.id}`}
                        show={item}
                        openPopover={openPopover}
                        setOpenPopover={setOpenPopover}
                        popoverPos={popoverPos}
                        setPopoverPos={setPopoverPos}
                      />
                    );
                  }
                  return (
                    <UnmatchedRow
                      type={item.type}
                      key={`${item.type}-${item.id}`}
                      item={item}
                      openPopover={openPopover}
                      setOpenPopover={setOpenPopover}
                      popoverPos={popoverPos}
                      setPopoverPos={setPopoverPos}
                      hasChevron={false}
                    />
                  );
                })}
              {activeFilter === "movies" &&
                filteredMovies.map((movie) => (
                  <UnmatchedRow
                    type="movie"
                    key={`movie-${movie.id}`}
                    item={movie}
                    openPopover={openPopover}
                    setOpenPopover={setOpenPopover}
                    popoverPos={popoverPos}
                    setPopoverPos={setPopoverPos}
                  />
                ))}
              {activeFilter === "shows" &&
                filteredShows.map((show) => (
                  <UnmatchedShowRow
                    type="show"
                    key={`show-${show.id}`}
                    show={show}
                    openPopover={openPopover}
                    setOpenPopover={setOpenPopover}
                    popoverPos={popoverPos}
                    setPopoverPos={setPopoverPos}
                  />
                ))}
              {activeFilter === "collections" &&
                filteredCollections.map((collection) => (
                  <UnmatchedRow
                    type="collection"
                    key={`collection-${collection.id}`}
                    item={collection}
                    openPopover={openPopover}
                    setOpenPopover={setOpenPopover}
                    popoverPos={popoverPos}
                    setPopoverPos={setPopoverPos}
                  />
                ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
export default UnmatchedAssets;
