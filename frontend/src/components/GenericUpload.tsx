import { useState } from "react";
import { Upload, Download, CheckCircle, AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";

interface GenericUploadProps {
    title: string;
    apiPath: string; // e.g., "fixed-deposits"
    redirectPath: string; // e.g., "/fixed-deposits"
    previewColumns: { header: string; accessor: string; format?: (val: any) => string }[];
}

export default function GenericUpload({ title, apiPath, redirectPath, previewColumns }: GenericUploadProps) {
    const [step, setStep] = useState<"upload" | "preview" | "success">("upload");
    const [file, setFile] = useState<File | null>(null);
    const [previewData, setPreviewData] = useState<any[]>([]);
    const [errors, setErrors] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleDownloadTemplate = () => {
        // Use the baseURL from api if available, otherwise fallback
        const baseURL = api.defaults.baseURL || "http://localhost:8000";
        window.location.href = `${baseURL}/${apiPath}/template`;
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setFile(e.target.files[0]);
        }
    };

    const handlePreview = async () => {
        if (!file) return;
        setLoading(true);
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await api.post(`/${apiPath}/preview-upload`, formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            setPreviewData(res.data.preview);
            setErrors(res.data.errors);
            setStep("preview");
        } catch (err: any) {
            console.error(err);
            const msg = err.response?.data?.detail || err.response?.statusText || "Upload failed. Check file format.";
            alert(`Upload failed: ${msg}`);
        } finally {
            setLoading(false);
        }
    };

    const handleConfirm = async () => {
        setLoading(true);
        try {
            await api.post(`/${apiPath}/confirm-upload`, previewData);
            setStep("success");
        } catch (err) {
            console.error(err);
            alert("Confirmation failed.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div className="flex items-center gap-4">
                <button onClick={() => navigate(redirectPath)} className="p-2 hover:bg-muted rounded-full">
                    <ArrowLeft className="w-5 h-5" />
                </button>
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{title}</h2>
                    <p className="text-muted-foreground">Bulk import data via CSV/Excel template.</p>
                </div>
            </div>

            {step === "upload" && (
                <div className="bg-card border rounded-xl p-8 space-y-8 shadow-sm">
                    <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg bg-muted/20 relative group">
                        <Upload className="w-12 h-12 text-muted-foreground mb-4 group-hover:text-primary transition-colors" />
                        <p className="text-lg font-medium">Drag and drop your file here</p>
                        <input
                            type="file"
                            onChange={handleFileChange}
                            className="absolute inset-0 opacity-0 cursor-pointer"
                        />
                        <p className="text-sm text-muted-foreground mt-2">{file ? file.name : "Select CSV or Excel file"}</p>
                    </div>

                    <div className="flex justify-between items-center">
                        <button
                            onClick={handleDownloadTemplate}
                            className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
                        >
                            <Download className="w-4 h-4" />
                            Download Template
                        </button>

                        <button
                            onClick={handlePreview}
                            disabled={!file || loading}
                            className="bg-primary text-primary-foreground px-6 py-2 rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50"
                        >
                            {loading ? "Processing..." : "Validate & Preview"}
                        </button>
                    </div>
                </div>
            )}

            {step === "preview" && (
                <div className="space-y-6">
                    {errors.length > 0 && (
                        <div className="bg-destructive/10 text-destructive p-4 rounded-lg flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 mt-0.5" />
                            <div>
                                <h4 className="font-semibold">Validation Errors ({errors.length})</h4>
                                <ul className="list-disc list-inside text-sm mt-1 max-h-32 overflow-y-auto">
                                    {errors.map((e, i) => (
                                        <li key={i}>Row {e.row}: {e.error}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}

                    <div className="bg-card border rounded-xl shadow-sm overflow-hidden">
                        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-white">
                            <h3 className="text-lg font-bold text-slate-900">Preview Data</h3>
                            <span className="text-xs font-bold text-slate-500 bg-slate-100 px-3 py-1 rounded-full">{previewData.length} Rows</span>
                        </div>
                        <div className="overflow-x-auto max-h-[500px]">
                            <table className="w-full text-left border-collapse min-w-max">
                                <thead className="bg-slate-50 text-slate-500 sticky top-0 z-10 border-b">
                                    <tr>
                                        {previewColumns.map(col => (
                                            <th key={col.accessor} className="px-6 py-3 text-xs font-bold uppercase tracking-wider">
                                                {col.header}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {previewData.map((row, idx) => (
                                        <tr key={idx} className="hover:bg-slate-50 transition-colors">
                                            {previewColumns.map(col => (
                                                <td key={col.accessor} className="px-6 py-3 whitespace-nowrap">
                                                    <span className="text-sm text-slate-600">
                                                        {col.format ? col.format(row[col.accessor]) : (row[col.accessor]?.toString() || "-")}
                                                    </span>
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div className="flex justify-end gap-3">
                        <button
                            onClick={() => setStep("upload")}
                            className="px-4 py-2 text-sm font-medium border rounded-lg hover:bg-muted"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleConfirm}
                            disabled={errors.length > 0 || previewData.length === 0 || loading}
                            className="bg-green-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                        >
                            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                            Confirm Import
                        </button>
                    </div>
                </div>
            )}

            {step === "success" && (
                <div className="flex flex-col items-center justify-center p-12 bg-card border rounded-xl space-y-4">
                    <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center">
                        <CheckCircle className="w-8 h-8" />
                    </div>
                    <h2 className="text-2xl font-bold">Import Successful!</h2>
                    <p className="text-lg text-muted-foreground">{previewData.length} records have been processed.</p>
                    <div className="flex gap-4">
                        <button onClick={() => setStep("upload")} className="text-primary hover:underline">Upload Another</button>
                        <button onClick={() => navigate(redirectPath)} className="bg-primary text-primary-foreground px-4 py-2 rounded-md">
                            Go to List
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
