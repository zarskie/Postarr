import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { useState } from "react";

function Navbar() {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="mx-auto max-w-6xl px-2 xl:px-0">
      <nav className="border-b border-gray-800 text-gray-400">
        <div className="flex items-center justify-between py-4">
          <img src="/logo.png" alt="/Logo" className="h-8 w-auto" />
          <ul className="m-0 hidden list-none gap-2 p-0 md:flex">
            <li>
              <Link
                to="/"
                className={`block cursor-pointer rounded-full px-3 py-2 transition-colors duration-200 hover:bg-gray-600 hover:text-white ${
                  location.pathname === "/" ? "text-white" : ""
                }`}
              >
                Dashboard
              </Link>
            </li>
            <li>
              <Link
                to="/settings"
                className={`block cursor-pointer rounded-full px-3 py-2 transition-colors duration-200 hover:bg-gray-600 hover:text-white ${
                  location.pathname === "/settings" ? "text-white" : ""
                }`}
              >
                Settings
              </Link>
            </li>
            {/* <li> */}
            {/*   <Link */}
            {/*     to="/logs" */}
            {/*     className={`block cursor-pointer rounded-full px-3 py-2 transition-colors duration-200 hover:bg-gray-600 hover:text-white ${ */}
            {/*       location.pathname === "/logs" ? "text-white" : "" */}
            {/*     }`} */}
            {/*   > */}
            {/*     Logs */}
            {/*   </Link> */}
            {/* </li> */}
          </ul>
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-2 text-gray-400 hover:text-white md:hidden"
          >
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
        {isMobileMenuOpen && (
          <div className="pb-4 md:hidden">
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              <li>
                <Link
                  to="/"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`block cursor-pointer rounded-md px-3 py-2 transition-colors duration-200 hover:bg-gray-600 hover:text-white ${
                    location.pathname === "/" ? "bg-gray-700 text-white" : ""
                  }`}
                >
                  Dashboard
                </Link>
              </li>
              <li>
                <Link
                  to="/settings"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`block cursor-pointer rounded-md px-3 py-2 transition-colors duration-200 hover:bg-gray-600 hover:text-white ${
                    location.pathname === "/settings"
                      ? "bg-gray-700 text-white"
                      : ""
                  }`}
                >
                  Settings
                </Link>
              </li>
              {/* <li> */}
              {/*   <Link */}
              {/*     to="/logs" */}
              {/*     onClick={() => setIsMobileMenuOpen(false)} */}
              {/*     className={`block cursor-pointer rounded-md px-3 py-2 transition-colors duration-200 hover:bg-gray-600 hover:text-white ${ */}
              {/*       location.pathname === "/logs" */}
              {/*         ? "bg-gray-700 text-white" */}
              {/*         : "" */}
              {/*     }`} */}
              {/*   > */}
              {/*     Logs */}
              {/*   </Link> */}
              {/* </li> */}
            </ul>
          </div>
        )}
      </nav>
    </div>
  );
}

export default Navbar;
