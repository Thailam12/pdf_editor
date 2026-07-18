#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Services
{
    enum class ExportFormat
    {
        PDF,
        PNG,
        JPEG,
        TIFF,
        BMP,
        SVG,
        Text,
        HTML,
        DOCX,
        XPS,
        PostScript
    };

    struct ExportService
    {
        ExportService();

        static ExportService GetDefault();

        bool ExportDocument(hstring const& sourcePath, hstring const& outputPath, ExportFormat format);
        bool ExportPage(int pageIndex, hstring const& outputPath, ExportFormat format, int dpi = 300);
        bool ExportPages(std::vector<int> const& pageIndices, hstring const& outputDir, ExportFormat format, int dpi = 300);

        bool ConvertToImage(hstring const& pdfPath, hstring const& outputDir, int dpi = 300);
        bool ConvertToText(hstring const& pdfPath, hstring const& outputPath);
        bool ConvertToHTML(hstring const& pdfPath, hstring const& outputPath);
        bool ConvertToDOCX(hstring const& pdfPath, hstring const& outputPath);

        std::vector<hstring> GetSupportedFormats() const;
        hstring GetFormatExtension(ExportFormat format) const;

    private:
        std::wstring ExecuteExportCommand(std::wstring const& command);
        bool ValidateOutputPath(hstring const& outputPath);
    };
}
