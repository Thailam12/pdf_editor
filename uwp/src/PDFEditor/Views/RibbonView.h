#pragma once

#include "Views/RibbonView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct RibbonView : RibbonViewT<RibbonView>
    {
        RibbonView();

        void SelectTab(hstring const& tabName);

    protected:
        void OnTabClick(Windows::Foundation::IInspectable const& sender,
                        Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnAIClick(Windows::Foundation::IInspectable const& sender,
                       Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnNewClick(Windows::Foundation::IInspectable const& sender,
                        Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnOpenClick(Windows::Foundation::IInspectable const& sender,
                         Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnSaveClick(Windows::Foundation::IInspectable const& sender,
                         Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnInsertImageClick(Windows::Foundation::IInspectable const& sender,
                                Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnInsertPageClick(Windows::Foundation::IInspectable const& sender,
                               Microsoft::UI::Xaml::RoutedEventArgs const& args);

    private:
        void ShowTabContent(hstring const& tabName);

        std::wstring m_activeTab{ L"Home" };
    };
}
