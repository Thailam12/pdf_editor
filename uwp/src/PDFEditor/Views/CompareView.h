#pragma once

#include "Views/CompareView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct CompareView : CompareViewT<CompareView>
    {
        CompareView();

        void CompareDocuments(hstring const& leftPath, hstring const& rightPath);

    protected:
        void OnBrowseLeftClick(Windows::Foundation::IInspectable const& sender,
                               Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnBrowseRightClick(Windows::Foundation::IInspectable const& sender,
                                Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnCompareClick(Windows::Foundation::IInspectable const& sender,
                            Microsoft::UI::Xaml::RoutedEventArgs const& args);

    private:
        std::wstring m_leftPath;
        std::wstring m_rightPath;

        winrt::Windows::Foundation::IAsyncAction BrowseForDocument(bool isLeft);
    };
}
