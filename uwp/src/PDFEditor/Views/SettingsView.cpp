#include "pch.h"
#include "Views/SettingsView.h"
#include "Views/SettingsView.g.cpp"
#include "Core/SettingsManager.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::PDFEditor::implementation
{
    SettingsView::SettingsView()
    {
        InitializeComponent();
        m_settings = Core::SettingsManager::GetDefault();
        LoadSettings();
    }

    void SettingsView::LoadSettings()
    {
        if (!m_settings) return;

        auto theme = m_settings->GetTheme();
        if (ThemeCombo())
        {
            if (theme == L"Dark") ThemeCombo().SelectedIndex(0);
            else if (theme == L"Light") ThemeCombo().SelectedIndex(1);
            else ThemeCombo().SelectedIndex(2);
        }

        if (DefaultZoomSlider())
            DefaultZoomSlider().Value(m_settings->GetDefaultZoom());

        if (AutoSaveToggle())
            AutoSaveToggle().IsOn(m_settings->GetAutoSaveEnabled());

        if (AutoSaveIntervalBox())
            AutoSaveIntervalBox().Text(winrt::to_hstring(m_settings->GetAutoSaveIntervalSeconds()));

        if (GridToggle())
            GridToggle().IsOn(m_settings->GetSetting(L"ShowGridLines") == L"true");

        if (SnapToggle())
            SnapToggle().IsOn(m_settings->GetSetting(L"SnapToGrid") == L"true");

        if (HQRenderToggle())
            HQRenderToggle().IsOn(m_settings->GetSetting(L"HighQualityRendering") == L"true");
    }

    void SettingsView::SaveSettings()
    {
        if (!m_settings) return;

        if (AutoSaveIntervalBox())
        {
            try
            {
                auto interval = std::stoul(std::wstring(AutoSaveIntervalBox().Text()));
                m_settings->SetAutoSaveIntervalSeconds(static_cast<uint32_t>(interval));
            }
            catch (...) {}
        }

        if (AIServerUrlBox())
        {
            m_settings->SetSetting(L"AIServerUrl", AIServerUrlBox().Text());
        }

        m_settings->Save();
    }

    void SettingsView::ResetDefaults()
    {
        if (m_settings)
        {
            m_settings->ResetToDefaults();
            LoadSettings();
        }
    }

    void SettingsView::OnThemeChanged(IInspectable const& sender,
                                       Controls::SelectionChangedEventArgs const& args)
    {
        auto combo = sender.as<Controls::ComboBox>();
        if (!combo || !m_settings) return;

        auto selectedItem = combo.SelectedItem().as<Controls::ComboBoxItem>();
        if (!selectedItem) return;

        auto tag = selectedItem.Tag();
        if (tag)
        {
            auto theme = winrt::unbox_value<hstring>(tag);
            m_settings->SetTheme(theme);
        }
    }

    void SettingsView::OnDefaultZoomChanged(IInspectable const&,
        Controls::Primitives::RangeBaseValueChangedEventArgs const& args)
    {
        if (m_settings)
        {
            m_settings->SetDefaultZoom(args.NewValue());
        }
    }

    void SettingsView::OnGridToggleChanged(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_settings && GridToggle())
        {
            m_settings->SetSetting(L"ShowGridLines", GridToggle().IsOn() ? L"true" : L"false");
        }
    }

    void SettingsView::OnSnapToggleChanged(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_settings && SnapToggle())
        {
            m_settings->SetSetting(L"SnapToGrid", SnapToggle().IsOn() ? L"true" : L"false");
        }
    }

    void SettingsView::OnHQRenderToggleChanged(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_settings && HQRenderToggle())
        {
            m_settings->SetSetting(L"HighQualityRendering", HQRenderToggle().IsOn() ? L"true" : L"false");
        }
    }

    void SettingsView::OnAutoSaveToggled(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_settings && AutoSaveToggle())
        {
            m_settings->SetAutoSaveEnabled(AutoSaveToggle().IsOn());
        }
    }

    void SettingsView::OnAIToggled(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_settings && AIToggle())
        {
            m_settings->SetSetting(L"AIEnabled", AIToggle().IsOn() ? L"true" : L"false");
        }
    }

    void SettingsView::OnTestConnectionClick(IInspectable const&, RoutedEventArgs const&)
    {
        OutputDebugStringW(L"[SettingsView] Testing AI connection...\n");
    }

    void SettingsView::OnSaveClick(IInspectable const&, RoutedEventArgs const&)
    {
        SaveSettings();
    }

    void SettingsView::OnResetClick(IInspectable const&, RoutedEventArgs const&)
    {
        ResetDefaults();
    }
}
