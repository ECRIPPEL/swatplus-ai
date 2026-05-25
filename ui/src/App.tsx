import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "@/components/Layout";
import Home from "@/routes/Home";
import SetupCheck from "@/routes/SetupCheck";
import Calibration from "@/routes/Calibration";
import Evaluation from "@/routes/Evaluation";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="/dashboard" element={<Navigate to="/" replace />} />
        <Route path="/chat" element={<Navigate to="/" replace />} />
        <Route path="/setup" element={<SetupCheck />} />
        <Route path="/calibration" element={<Calibration />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
