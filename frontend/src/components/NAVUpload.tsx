import { useState } from "react";
import { Upload, CheckCircle, AlertCircle } from "lucide-react";
import api from "../lib/api";

export default function NAVUpload() {
    const [uploading, setUploading] = useState(false);
    const [status, setStatus] = useState<{ type: 'success' | 'error' | null, message: string }>({ type: null, message: '' });

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        setStatus({ type: null, message: '' });

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await api.post('/nav/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            setStatus({
                type: 'success',
                message: `✓ ${response.data.message}. Total cached: ${response.data.total_cached} entries.`
            });

            // Trigger a page reload after 2 seconds to refresh NAV values
            setTimeout(() => {
                window.location.reload();
            }, 2000);

        } catch (err: any) {
            setStatus({
                type: 'error',
                message: err.response?.data?.detail || 'Failed to upload NAV file'
            });
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center gap-3 mb-4">
                <div className="bg-indigo-100 p-2 rounded-lg">
                    <Upload className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                    <h3 className="font-black text-slate-900 uppercase text-sm">Update NAV Data</h3>
                    <p className="text-xs text-slate-500">Upload NAVOpen.txt for accurate daily NAV values</p>
                </div>
            </div>

            <div className="space-y-3">
                <label className="block">
                    <input
                        type="file"
                        accept=".txt,.csv"
                        onChange={handleFileUpload}
                        disabled={uploading}
                        className="block w-full text-sm text-slate-500
                            file:mr-4 file:py-2 file:px-4
                            file:rounded-lg file:border-0
                            file:text-sm file:font-bold
                            file:bg-indigo-50 file:text-indigo-700
                            hover:file:bg-indigo-100
                            file:cursor-pointer cursor-pointer
                            disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                </label>

                {uploading && (
                    <div className="flex items-center gap-2 text-sm text-slate-600">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
                        <span>Processing NAV file...</span>
                    </div>
                )}

                {status.type === 'success' && (
                    <div className="flex items-start gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                        <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-emerald-800 font-semibold">{status.message}</p>
                    </div>
                )}

                {status.type === 'error' && (
                    <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-red-800 font-semibold">{status.message}</p>
                    </div>
                )}

                <div className="text-xs text-slate-400 space-y-1">
                    <p>• Expected format: Semicolon-separated (;)</p>
                    <p>• Columns: Scheme Code;ISIN;ISIN2;Scheme Name;NAV;Date</p>
                    <p>• NAV values will be cached and used for all mutual fund calculations</p>
                </div>
            </div>
        </div>
    );
}
