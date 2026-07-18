#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Services
{
    struct PDFService
    {
        PDFService();

        static PDFService GetDefault();

        bool OpenDocument(hstring const& filePath);
        bool SaveDocument(hstring const& filePath);
        bool SaveDocumentAs(hstring const& filePath);
        void CloseDocument();

        int GetPageCount() const;
        Windows::Foundation::IAsyncAction RenderPage(int pageIndex, int width, int height);

        std::vector<hstring> SearchText(hstring const& query, bool matchCase, bool wholeWord);
        bool InsertText(int pageIndex, double x, double y, hstring const& text, hstring const& fontName, double fontSize);
        bool DeleteElement(int pageIndex, hstring const& elementId);
        bool MoveElement(int pageIndex, hstring const& elementId, double newX, double newY);

        bool AddAnnotation(int pageIndex, hstring const& type, double x, double y, double width, double height, hstring const& content);
        bool RemoveAnnotation(int pageIndex, hstring const& annotationId);

        bool InsertPage(int position);
        bool DeletePage(int pageIndex);
        bool RotatePage(int pageIndex, int degrees);
        bool CropPage(int pageIndex, double left, double top, double width, double height);
        bool ExtractPages(std::vector<int> const& pageIndices, hstring const& outputPath);
        bool MergeDocuments(std::vector<hstring> const& filePaths);
        bool SplitDocument(std::vector<int> const& splitPoints, hstring const& outputDir);

        Windows::Foundation::IAsyncAction GetPageThumbnail(int pageIndex, int width, int height);

    private:
        std::wstring m_currentDocumentPath;
        int m_pageCount{ 0 };
        bool m_isModified{ false };
        std::mutex m_mutex;

        std::wstring ExecutePythonCommand(std::wstring const& command);
        std::wstring GetPythonExecutablePath() const;
    };
}
