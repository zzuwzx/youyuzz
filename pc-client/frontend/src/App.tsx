import { Routes, Route } from "react-router-dom"
import MainPage from "./pages/MainPage"
import SettingsPage from "./pages/SettingsPage"
import VIPPage from "./pages/VIPPage"

export default function App() {
  return (
    <div className="min-h-screen bg-bg">
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/vip" element={<VIPPage />} />
      </Routes>
    </div>
  )
}
