import { Image, ImageOff } from "lucide-react";
import { useState } from "react";
import PosterViewer from "../components/dashboard/PosterViewer";

function Home() {
  const [activeSection, setActiveSection] = useState("poster-viewer");
  const sections = [
    { id: "poster-viewer", label: "Poster Viewer", icon: Image },
    { id: "unmatched-assets", label: "Unmatched Assets", icon: ImageOff },
  ];
  return (
    <div>
      <h1 className="mb-6 px-4 text-2xl font-bold text-white xl:px-0">
        Dashboard
      </h1>
      <div className="mx-2 flex flex-col rounded-lg bg-gray-800 py-2 md:flex-row xl:mx-0">
        {/* Left Navigation */}
        <nav className="w-full flex-shrink-0 border-gray-700 md:w-48 md:border-r">
          <ul className="flex flex-col overflow-x-auto text-sm md:flex-col md:overflow-x-visible">
            {sections.map((section) => {
              const Icon = section.icon;
              const isActive = activeSection === section.id;
              return (
                <li key={section.id} className="flex-shrink-0">
                  <button
                    onClick={() => {
                      setActiveSection(section.id);
                    }}
                    className={`relative flex w-full items-center gap-3 whitespace-nowrap px-4 py-2 text-left transition-colors ${
                      activeSection === section.id
                        ? "bg-gray-700 text-white"
                        : "text-gray-400 hover:bg-gray-700 hover:text-white"
                    }`}
                  >
                    <span
                      className={`absolute left-0 top-0 h-full w-1 rounded-r ${isActive ? "bg-blue-500" : "bg-transparent"}`}
                    />
                    <Icon size={22} />
                    <span className="flex-1">{section.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="flex-1 p-4 md:p-6">
          {/* Poster Viewer Sections */}
          {activeSection === "poster-viewer" && (
            <>
              <div className="mb-6 flex flex-col gap-3 border-b border-gray-700 pb-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="mb-2 text-xl font-semibold text-white">
                    Poster Viewer
                  </h2>
                  <p className="text-sm text-gray-400">View plex assets.</p>
                </div>
              </div>
              <div
                className={activeSection === "poster-viewer" ? "" : "hidden"}
              >
                <PosterViewer />
              </div>
            </>
          )}
          {/* Unmatched Assets Section */}
          {activeSection === "unmatched-assets" && (
            <div className="mb-6 flex flex-col gap-3 border-b border-gray-700 pb-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="mb-2 text-xl font-semibold text-white">
                  Unmatched Assets
                </h2>
                <p className="text-sm text-gray-400">View unmatched assets.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Home;
