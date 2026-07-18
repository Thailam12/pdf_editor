#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Controls
{
    struct RibbonBar : winrt::Microsoft::UI::Xaml::Controls::Control
    {
        RibbonBar();

        void SetActiveTab(hstring const& tabName);
        hstring GetActiveTab() const;

        event_token TabChanged(Microsoft::UI::Xaml::RoutedEventHandler const& handler);
        void TabChanged(event_token const& token) noexcept;

    private:
        std::wstring m_activeTab{ L"Home" };
        Microsoft::UI::Xaml::Controls::StackPanel m_tabHeaders{ nullptr };
        Microsoft::UI::Xaml::Controls::Grid m_contentArea{ nullptr };
        Microsoft::UI::RoutedEventHandler m_tabChangedHandler;
    };
}
