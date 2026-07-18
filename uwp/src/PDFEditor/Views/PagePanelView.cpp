#include "pch.h"
#include "Views/PagePanelView.h"
#include "Views/PagePanelView.g.cpp"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::PDFEditor::implementation
{
    PagePanelView::PagePanelView()
    {
        InitializeComponent();
        RefreshThumbnails();
    }

    uint32_t PagePanelView::SelectedPageIndex() { return m_selectedIndex; }

    void PagePanelView::SelectedPageIndex(uint32_t value)
    {
        m_selectedIndex = value;
        if (ThumbnailsList())
        {
            ThumbnailsList().SelectedIndex(value);
        }
    }

    void PagePanelView::RefreshThumbnails()
    {
        auto docManager = Core::DocumentManager::GetDefault();
        if (!docManager || !docManager->CurrentDocument())
        {
            m_pageCount = 0;
            if (ThumbnailsList())
            {
                auto items = winrt::single_threaded_vector<hstring>();
                ThumbnailsList().ItemsSource(items);
            }
            return;
        }

        auto doc = docManager->CurrentDocument();
        m_pageCount = doc.PageCount();
        if (m_pageCount == 0) m_pageCount = 1;

        auto items = winrt::single_threaded_vector<hstring>();
        for (uint32_t i = 0; i < m_pageCount; ++i)
        {
            items.Append(L"Page " + winrt::to_hstring(i + 1));
        }

        if (ThumbnailsList())
        {
            ThumbnailsList().ItemsSource(items);
        }
    }

    void PagePanelView::OnCollapseClick(IInspectable const&, RoutedEventArgs const&)
    {
        this->Visibility(Visibility::Collapsed);
    }

    void PagePanelView::OnThumbnailClick(IInspectable const& sender,
                                          Input::PointerRoutedEventArgs const&)
    {
        auto element = sender.as<Controls::Grid>();
        if (!element) return;

        auto tag = element.Tag();
        if (tag)
        {
            auto index = winrt::unbox_value<int32_t>(tag);
            m_selectedIndex = static_cast<uint32_t>(index);

            auto docManager = Core::DocumentManager::GetDefault();
            if (docManager && docManager->CurrentDocument())
            {
                docManager->CurrentDocument().CurrentPage(index);
            }
        }
    }
}
