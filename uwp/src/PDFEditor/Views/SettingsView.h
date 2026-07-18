#pragma once

#include "Views/SettingsView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct SettingsView : SettingsViewT<SettingsView>
    {
        SettingsView();

        void LoadSettings();
        void SaveSettings();
        void ResetDefaults();

    protected:
        void OnThemeChanged(Windows::Foundation::IInspectable const& sender,
                            Microsoft::UI::Xaml::Controls::SelectionChangedEventArgs const& args);
        void OnDefaultZoomChanged(Windows::Foundation::IInspectable const& sender,
                                  Microsoft::UI::Xaml::Controls::Primitives::RangeBaseValueChangedEventArgs const& args);
        void OnGridToggleChanged(Windows::Foundation::IInspectable const& sender,
                                 Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnSnapToggleChanged(Windows::Foundation::IInspectable const& sender,
                                 Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnHQRenderToggleChanged(Windows::Foundation::IInspectable const& sender,
                                     Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnAutoSaveToggled(Windows::Foundation::IInspectable const& sender,
                               Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnAIToggled(Windows::Foundation::IInspectable const& sender,
                         Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnTestConnectionClick(Windows::Foundation::IInspectable const& sender,
                                   Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnSaveClick(Windows::Foundation::IInspectable const& sender,
                         Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnResetClick(Windows::Foundation::IInspectable const& sender,
                          Microsoft::UI::Xaml::RoutedEventArgs const& args);

    private:
        Core::SettingsManager m_settings{ nullptr };
    };
}
