import { Routes, Route } from "react-router-dom";
import { CandidateProvider } from "./contexts/CandidateContext";
import { DrawerProvider }    from "./contexts/DrawerContext";
import { ToastProvider }     from "./contexts/ToastContext";
import Sidebar               from "./components/Sidebar";
import Topbar                from "./components/Topbar";
import CandidateDrawer       from "./components/CandidateDrawer";
import Dashboard             from "./pages/Dashboard";
import Upload                from "./pages/Upload";
import Search                from "./pages/Search";

export default function App() {
  return (
    <CandidateProvider>
      <DrawerProvider>
        <ToastProvider>
          <div className="app-shell">
            <Sidebar />
            <Topbar />
            <main className="main-content">
              <Routes>
                <Route path="/"       element={<Dashboard />} />
                <Route path="/upload" element={<Upload />}    />
                <Route path="/search" element={<Search />}    />
              </Routes>
            </main>
          </div>
          <CandidateDrawer />
        </ToastProvider>
      </DrawerProvider>
    </CandidateProvider>
  );
}
