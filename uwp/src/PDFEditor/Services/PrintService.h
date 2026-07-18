#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Services
{
    struct PrintSettings
    {
        hstring PrinterName;
        int StartPage{ 0 };
        int EndPage{ -1 };
        int Copies{ 1 };
        bool Collate{ true };
        bool Duplex{ false };
        bool Color{ true };
        bool FitToPage{ true };
        bool PrintAsImage{ false };
    };

    struct PrintService
    {
        PrintService();

        static PrintService GetDefault();

        bool PrintDocument(hstring const& filePath, PrintSettings const& settings);
        bool PrintPages(hstring const& filePath, std::vector<int> const& pageIndices, PrintSettings const& settings);

        std::vector<hstring> GetAvailablePrinters() const;
        hstring GetDefaultPrinter() const;
        bool IsPrintingSupported() const;

        void ShowPrintDialog(hstring const& filePath);

    private:
        bool ExecutePrintCommand(hstring const& command);
        std::wstring BuildPrintArguments(hstring const& filePath, PrintSettings const& settings);
    };
}
