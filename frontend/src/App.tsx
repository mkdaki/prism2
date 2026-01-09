import { BrowserRouter, Route, Routes } from "react-router-dom";
import DatasetListPage from "./pages/DatasetListPage";
import UploadPage from "./pages/UploadPage";
import DatasetDetailPage from "./pages/DatasetDetailPage";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<DatasetListPage />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/datasets/:datasetId" element={<DatasetDetailPage />} />
            </Routes>
        </BrowserRouter>
    );
}
