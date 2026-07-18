#pragma once

#include "Views/SearchView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct SearchView : SearchViewT<SearchView>
    {
        SearchView();

        void Search(hstring const& query);
        void ReplaceAll(hstring const& find, hstring const& replace);
        void ReplaceSelected(hstring const& find, hstring const& replace);

    protected:
        void OnFindNextClick(Windows::Foundation::IInspectable const& sender,
                             Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnFindAllClick(Windows::Foundation::IInspectable const& sender,
                            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnReplaceClick(Windows::Foundation::IInspectable const& sender,
                            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnReplaceAllClick(Windows::Foundation::IInspectable const& sender,
                               Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnResultItemClick(Windows::Foundation::IInspectable const& sender,
                               Microsoft::UI::Xaml::Controls::ItemClickEventArgs const& args);

    private:
        int m_currentResultIndex{ 0 };
        std::vector<std::tuple<int, int, std::wstring>> m_results;
    };
}
