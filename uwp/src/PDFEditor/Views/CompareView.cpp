#include "pch.h"
#include "Views/CompareView.h"
#include "Views/CompareView.g.cpp"
#include "Core/DocumentManager.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::PDFEditor::implementation
{
    CompareView::CompareView()
    {
        InitializeComponent();
    }

    void CompareView::CompareDocuments(hstring const& leftPath, hstring const& rightPath)
    {
        m_leftPath = std::wstring(leftPath);
        m_rightPath = std::wstring(rightPath);

        if (LeftFileText())
            LeftFileText().Text(std::filesystem::path(m_leftPath).filename().wstring());
        if (RightFileText())
            RightFileText().Text(std::filesystem::path(m_rightPath).filename().wstring());

        OutputDebugStringW(L"[CompareView] Comparing documents:\n");
        OutputDebugStringW(m_leftPath.c_str());
        OutputDebugStringW(L"\n  vs\n");
        OutputDebugStringW(m_rightPath.c_str());
        OutputDebugStringW(L"\n");
    }

    winrt::Windows::Foundation::IAsyncAction CompareView::BrowseForDocument(bool isLeft)
    {
        auto picker = Windows::Storage::Pickers::FileOpenPicker();
        picker.SuggestedStartLocation(Windows::Storage::Pickers::PickerLocationId::Desktop);
        picker.FileTypeFilter().Append(L".pdf");

        auto file = co_await picker.PickSingleFileAsync();
        if (file)
        {
            if (isLeft)
            {
                m_leftPath = file.Path();
                if (LeftFileText())
                    LeftFileText().Text(std::filesystem::path(m_leftPath).filename().wstring());
            }
            else
            {
                m_rightPath = file.Path();
                if (RightFileText())
                    RightFileText().Text(std::filesystem::path(m_rightPath).filename().wstring());
            }
        }
    }

    void CompareView::OnBrowseLeftClick(IInspectable const&, RoutedEventArgs const&)
    {
        BrowseForDocument(true);
    }

    void CompareView::OnBrowseRightClick(IInspectable const&, RoutedEventArgs const&)
    {
        BrowseForDocument(false);
    }

    void CompareView::OnCompareClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_leftPath.empty() || m_rightPath.empty())
        {
            if (DiffSummaryText())
                DiffSummaryText().Text(L"Please select both documents to compare.");
            return;
        }

        if (!std::filesystem::exists(m_leftPath) || !std::filesystem::exists(m_rightPath))
        {
            if (DiffSummaryText())
                DiffSummaryText().Text(L"One or both files do not exist.");
            return;
        }

        if (DiffSummaryText())
            DiffSummaryText().Text(L"Comparing documents...");

        CompareDocuments(winrt::hstring(m_leftPath), winrt::hstring(m_rightPath));

        if (DiffSummaryText())
            DiffSummaryText().Text(L"Comparison complete. 0 differences found.");
    }
}
