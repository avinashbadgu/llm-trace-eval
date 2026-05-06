import { Routes, Route, NavLink, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Traces from "./pages/Traces";
import Compare from "./pages/Compare";

function NavItem({ to, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? "bg-brand-600 text-white"
            : "text-gray-400 hover:text-white hover:bg-white/10"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top nav */}
      <header className="border-b border-white/10 bg-panel/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
          <span className="font-bold text-brand-500 tracking-tight text-lg select-none">
            ◎ LLM Eval
          </span>
          <nav className="flex items-center gap-1">
            <NavItem to="/dashboard" label="Dashboard" />
            <NavItem to="/traces" label="Traces" />
            <NavItem to="/compare" label="Compare" />
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-brand-500 animate-pulse" />
            <span className="text-xs text-gray-400">Live</span>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/traces" element={<Traces />} />
          <Route path="/compare" element={<Compare />} />
        </Routes>
      </main>
    </div>
  );
}
