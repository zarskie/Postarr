import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/layout/Navbar';
import Home from './pages/Home'
import Settings from './pages/Settings'
import Logs from './pages/Logs'

function App() {
  return (
    <Router>
        <div 
            className='min-h-screen bg-repeat'
            style={{ 
                backgroundImage: "url('/background.png')",
                backgroundColor: '#000000'
            }}
        >
          <Navbar />
          <main className='max-w-6xl mx-auto py-8'>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/logs" element={<Logs />} />
            </Routes>
          </main>
        </div>
    </Router>
  );
}

export default App;
