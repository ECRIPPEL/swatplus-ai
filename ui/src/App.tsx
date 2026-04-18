import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/routes/Dashboard";
import SetupCheck from "@/routes/SetupCheck";
import Calibration from "@/routes/Calibration";
import Evaluation from "@/routes/Evaluation";
import Chat from "@/routes/Chat";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/setup" element={<SetupCheck />} />
        <Route path="/calibration" element={<Calibration />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
