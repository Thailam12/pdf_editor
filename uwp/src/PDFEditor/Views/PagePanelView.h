#pragma once

#include "Views/PagePanelView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct PagePanelView : PagePanelViewT<PagePanelView>
    {
        PagePanelView();

        uint32_t SelectedPageIndex();
        void SelectedPageIndex(uint32_t value);
        void RefreshThumbnails();

    protected:
        void OnCollapseClick(Windows::Foundation::IInspectable const& sender,
                             Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnThumbnailClick(Windows::Foundation::IInspectable const& sender,
                              Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);

    private:
        uint32_t m_selectedIndex{ 0 };
        uint32_t m_pageCount{ 0 };
    };
}
