import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { useState } from "react";

function Navbar() {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="max-w-6xl mx-auto px-2 md:px-0">
      <nav className="text-gray-400 border-b border-gray-800">
        <div className="py-4 flex items-center justify-between">
          <img src="/logo.png" alt="/Logo" className="h-8 w-auto" />
          <ul className="hidden md:flex gap-2 list-none m-0 p-0">
            <li>
              <Link
                to="/"
                className={`cursor-pointer hover:text-white hover:bg-gray-600 transition-colors duration-200 px-3 py-2 rounded-full block ${
                  location.pathname === "/" ? "text-white" : ""
                }`}
              >
                Poster Renamerr
              </Link>
            </li>
            <li>
              <Link
                to="/settings"
                className={`cursor-pointer hover:text-white hover:bg-gray-600 transition-colors duration-200 px-3 py-2 rounded-full block ${
                  location.pathname === "/settings" ? "text-white" : ""
                }`}
              >
                Settings
              </Link>
            </li>
            <li>
              <Link
                to="/logs"
                className={`cursor-pointer hover:text-white hover:bg-gray-600 transition-colors duration-200 px-3 py-2 rounded-full block ${
                  location.pathname === "/logs" ? "text-white" : ""
                }`}
              >
                Logs
              </Link>
            </li>
          </ul>
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden text-gray-400 hover:text-white p-2"
          >
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
        {isMobileMenuOpen && (
          <div className="md:hidden pb-4">
            <ul className="flex flex-col gap-2 list-none m-0 p-0">
              <li>
                <Link
                  to="/"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`cursor-pointer hover:text-white hover:bg-gray-600 transition-colors duration-200 px-3 py-2 rounded-md block ${
                    location.pathname === "/" ? "text-white bg-gray-700" : ""
                  }`}
                >
                  Poster Renamerr
                </Link>
              </li>
              <li>
                <Link
                  to="/settings"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`cursor-pointer hover:text-white hover:bg-gray-600 transition-colors duration-200 px-3 py-2 rounded-md block ${
                    location.pathname === "/settings"
                      ? "text-white bg-gray-700"
                      : ""
                  }`}
                >
                  Settings
                </Link>
              </li>
              <li>
                <Link
                  to="/logs"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`cursor-pointer hover:text-white hover:bg-gray-600 transition-colors duration-200 px-3 py-2 rounded-md block ${
                    location.pathname === "/logs"
                      ? "text-white bg-gray-700"
                      : ""
                  }`}
                >
                  Logs
                </Link>
              </li>
            </ul>
          </div>
        )}
      </nav>
    </div>
  );
}

export default Navbar;
