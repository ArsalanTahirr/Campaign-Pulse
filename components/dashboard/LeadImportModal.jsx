"use client";

import React, { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  UploadCloud,
  FileText,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  X,
  ChevronRight,
  ArrowLeft,
  Loader2,
} from "lucide-react";
import Papa from "papaparse";
import * as XLSX from "xlsx";
import { toast } from "sonner";
import { messageFromApiErrorBody } from "@/utils/apiError";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export default function LeadImportModal({
  isOpen,
  onClose,
  workspaceId,
  campaignId,
  onUploaded,
}) {
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [previewData, setPreviewData] = useState({ headers: [], rows: [], totalRows: 0 });
  const [hasEmailColumn, setHasEmailColumn] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const resetState = useCallback(() => {
    setStep(1);
    setFile(null);
    setPreviewData({ headers: [], rows: [], totalRows: 0 });
    setHasEmailColumn(false);
    setParsing(false);
    setUploading(false);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [onClose, resetState]);

  // Handle outside click or escape
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  const processFile = async (selectedFile) => {
    if (!selectedFile) return;

    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      toast.error(`File size must be under ${MAX_FILE_SIZE_MB}MB.`);
      return;
    }

    const name = selectedFile.name.toLowerCase();
    const isCSV = name.endsWith(".csv");
    const isExcel = name.endsWith(".xlsx");

    if (!isCSV && !isExcel) {
      toast.error("Please upload a .csv or .xlsx file.");
      return;
    }

    setFile(selectedFile);
    setParsing(true);
    setStep(2);

    try {
      if (isCSV) {
        Papa.parse(selectedFile, {
          header: true,
          skipEmptyLines: "greedy",
          complete: (results) => {
            const headers = results.meta.fields || [];
            const hasEmail = headers.some((h) => h.toLowerCase() === "email");
            setHasEmailColumn(hasEmail);
            setPreviewData({
              headers,
              rows: results.data.slice(0, 4),
              totalRows: results.data.length,
            });
            setParsing(false);
          },
          error: () => {
            toast.error("Failed to parse CSV file.");
            setParsing(false);
            setStep(1);
          },
        });
      } else if (isExcel) {
        const buffer = await selectedFile.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: "array" });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const json = XLSX.utils.sheet_to_json(worksheet, { header: 1, blankrows: false });

        if (json.length > 0) {
          const headers = json[0] || [];
          const rows = json.slice(1);
          const hasEmail = headers.some((h) => h?.toString().toLowerCase() === "email");
          setHasEmailColumn(hasEmail);

          // Convert rows to object format for preview consistency
          const formattedRows = rows.slice(0, 4).map((rowArray) => {
            let rowObj = {};
            headers.forEach((h, i) => {
              rowObj[h] = rowArray[i];
            });
            return rowObj;
          });

          setPreviewData({
            headers,
            rows: formattedRows,
            totalRows: rows.length,
          });
        } else {
          toast.error("The Excel file appears to be empty.");
          setStep(1);
        }
        setParsing(false);
      }
    } catch (err) {
      toast.error("An error occurred while parsing the file.");
      setParsing(false);
      setStep(1);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const selectedFile = e.dataTransfer.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const handleImport = async () => {
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/leads/import`,
        { method: "POST", credentials: "include", body: form }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Upload failed."));
      }
      const session = await res.json();
      toast.success(
        `Imported ${session.imported_count} leads (${session.skipped_count} skipped, ${session.error_count} errors).`
      );
      onUploaded?.();
      handleClose();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm sm:p-6"
      onMouseDown={handleBackdropClick}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        transition={{ duration: 0.2 }}
        className="flex w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl dark:bg-slate-900"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5 dark:border-slate-800">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Import Leads
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Upload your contacts in CSV or Excel format
            </p>
          </div>
          <button
            onClick={handleClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="relative min-h-[400px] bg-slate-50/50 px-6 py-8 dark:bg-slate-900/50">
          <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2 }}
                className="flex h-full flex-col items-center justify-center"
              >
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={[
                    "flex w-full max-w-xl cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition-all",
                    isDragging
                      ? "border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-500/10"
                      : "border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/50 dark:border-slate-700 dark:bg-slate-800/50 dark:hover:border-blue-500/50",
                  ].join(" ")}
                >
                  <div className="mb-4 rounded-full bg-blue-100 p-4 dark:bg-blue-900/50">
                    <UploadCloud className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                  </div>
                  <h3 className="mb-2 text-base font-medium text-slate-900 dark:text-slate-200">
                    Click to upload or drag and drop
                  </h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Accepted formats: .csv, .xlsx
                  </p>
                  <p className="mt-4 text-xs text-slate-400 dark:text-slate-500">
                    Maximum file size {MAX_FILE_SIZE_MB}MB. Row 1 must contain headers.
                  </p>
                </div>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".csv,.xlsx"
                  className="hidden"
                />
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2 }}
                className="flex h-full flex-col"
              >
                {parsing ? (
                  <div className="flex flex-1 flex-col items-center justify-center space-y-4">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                    <p className="text-sm text-slate-500">Parsing file...</p>
                  </div>
                ) : (
                  <div className="flex flex-1 flex-col">
                    <div className="mb-6 flex items-start justify-between">
                      <div>
                        <h3 className="flex items-center gap-2 text-base font-medium text-slate-900 dark:text-slate-100">
                          {file?.name.endsWith(".csv") ? (
                            <FileText className="h-5 w-5 text-emerald-500" />
                          ) : (
                            <FileSpreadsheet className="h-5 w-5 text-emerald-500" />
                          )}
                          Format Preview
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                          {previewData.totalRows.toLocaleString()} rows detected. Review mapping below.
                        </p>
                      </div>
                      <button
                        onClick={() => setStep(1)}
                        className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        Change file
                      </button>
                    </div>

                    {!hasEmailColumn && (
                      <div className="mb-6 flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700 dark:border-rose-900/50 dark:bg-rose-900/20 dark:text-rose-400">
                        <AlertCircle className="h-5 w-5 shrink-0" />
                        <div className="text-sm">
                          <strong>Missing Email Column:</strong> We couldn't detect an 'email' column.
                          Please ensure your file has a header named exactly "email" or "Email".
                        </div>
                      </div>
                    )}

                    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                          <thead className="bg-slate-50 text-xs uppercase text-slate-500 dark:bg-slate-900/50 dark:text-slate-400">
                            <tr>
                              {previewData.headers.map((header, idx) => {
                                const isEmail = header?.toString().toLowerCase() === "email";
                                return (
                                  <th
                                    key={idx}
                                    className={[
                                      "px-4 py-3 font-semibold",
                                      isEmail ? "bg-blue-50/50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400" : "",
                                    ].join(" ")}
                                  >
                                    <div className="flex items-center gap-1.5">
                                      {header}
                                      {isEmail && <CheckCircle2 className="h-3.5 w-3.5" />}
                                    </div>
                                  </th>
                                );
                              })}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {previewData.rows.map((row, rowIdx) => (
                              <tr key={rowIdx}>
                                {previewData.headers.map((header, colIdx) => {
                                  const isEmail = header?.toString().toLowerCase() === "email";
                                  return (
                                    <td
                                      key={colIdx}
                                      className={[
                                        "truncate px-4 py-3 max-w-[200px] text-slate-600 dark:text-slate-300",
                                        isEmail ? "bg-blue-50/20 dark:bg-blue-900/10" : "",
                                      ].join(" ")}
                                    >
                                      {row[header]?.toString() || "—"}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {previewData.totalRows > 4 && (
                        <div className="bg-slate-50 py-2 text-center text-xs text-slate-500 dark:bg-slate-900/50">
                          Showing first 4 rows
                        </div>
                      )}
                    </div>

                    <div className="mt-auto pt-8 flex justify-end">
                      <button
                        onClick={() => setStep(3)}
                        disabled={!hasEmailColumn}
                        className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Continue
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
              </motion.div>
            )}

            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2 }}
                className="flex h-full flex-col items-center justify-center text-center"
              >
                <div className="mb-6 rounded-full bg-emerald-100 p-4 dark:bg-emerald-900/50">
                  <CheckCircle2 className="h-10 w-10 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
                  Ready to Import
                </h3>
                <p className="mb-8 text-base text-slate-500 dark:text-slate-400 max-w-md">
                  We found <strong>{previewData.totalRows.toLocaleString()} rows</strong> in{" "}
                  <strong>{file?.name}</strong>. The standard columns will be mapped, and any extras will be saved as custom fields.
                </p>

                <div className="flex gap-3">
                  <button
                    onClick={() => setStep(2)}
                    disabled={uploading}
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-6 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back
                  </button>
                  <button
                    onClick={handleImport}
                    disabled={uploading}
                    className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {uploading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <UploadCloud className="h-4 w-4" />
                    )}
                    Import Leads
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
