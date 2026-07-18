#include "pch.h"
#include "Controls/RibbonBar.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::PDFEditor::Controls
{
    RibbonBar::RibbonBar()
    {
        m_tabHeaders = Microsoft::UI::Xaml::Controls::StackPanel();
        m_tabHeaders.Orientation(Microsoft::UI::Xaml::Controls::Orientation::Horizontal);

        m_contentArea = Microsoft::UI::Xaml::Controls::Grid();
    }

    void RibbonBar::SetActiveTab(hstring const& tabName)
    {
        m_activeTab = std::wstring(tabName);
        if (m_tabChangedHandler)
        {
            m_tabChangedHandler(nullptr, RoutedEventArgs());
        }
    }

    hstring RibbonBar::GetActiveTab() const
    {
        return m_activeTab;
    }

    event_token RibbonBar::TabChanged(RoutedEventHandler const& handler)
    {
        return m_tabChangedHandler.add(handler);
    }

    void RibbonBar::TabChanged(event_token const& token) noexcept
    {
        m_tabChangedHandler.remove(token);
    }
}
