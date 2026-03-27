import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/layout/Navbar";
import Home from "./pages/Home";
import Settings from "./pages/Settings";
import Logs from "./pages/Logs";
import RunCommands from "./components/layout/RunCommands";
import { PosterProvider } from "./context/PosterProvider";
import { UnmatchedProvider } from "./context/UnmatchedProvider";

function App() {
  return (
    <Router>
      <UnmatchedProvider>
        <PosterProvider>
          <div
            className="min-h-screen bg-repeat"
            style={{
              backgroundImage: "url('/background.png')",
              backgroundColor: "#000000",
            }}
          >
            <Navbar />
            <main className="mx-auto max-w-6xl py-8">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/logs" element={<Logs />} />
              </Routes>
            </main>
            <RunCommands />
          </div>
        </PosterProvider>
      </UnmatchedProvider>
    </Router>
  );
}

export default App;
