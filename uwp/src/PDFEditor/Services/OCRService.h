#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Services
{
    struct OCRResult
    {
        hstring Text;
        double Confidence;
        double X;
        double Y;
        double Width;
        double Height;
        int PageIndex;
    };

    struct OCRService
    {
        OCRService();

        static OCRService GetDefault();

        winrt::Windows::Foundation::IAsyncOperation<hstring> RecognizeTextAsync(int pageIndex);
        winrt::Windows::Foundation::IAsyncOperation<hstring> RecognizeTextInRegionAsync(int pageIndex,
            double x, double y, double width, double height);
        std::vector<OCRResult> GetDetailedResults() const;

        bool IsOCRAvailable() const;
        void SetLanguage(hstring const& languageCode);
        hstring GetLanguage() const;

    private:
        std::wstring ExecuteOCRCommand(std::wstring const& command);
        std::vector<OCRResult> ParseOCRResults(std::wstring const& jsonResults);

        std::wstring m_languageCode{ L"eng" };
        std::vector<OCRResult> m_lastResults;
        std::mutex m_mutex;
    };
}
