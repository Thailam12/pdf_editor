#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Controls
{
    struct ColorPicker : winrt::Microsoft::UI::Xaml::Controls::Control
    {
        ColorPicker();

        Windows::UI::Color SelectedColor() const { return m_selectedColor; }
        void SelectedColor(Windows::UI::Color value);
        double Opacity() const { return m_opacity; }
        void Opacity(double value);
        bool ShowAlpha() const { return m_showAlpha; }
        void ShowAlpha(bool value);

        winrt::event_token ColorChanged(winrt::Windows::Foundation::EventHandler<Windows::UI::Color> const& handler);
        void ColorChanged(winrt::event_token const& token) noexcept;

    private:
        void BuildUI();
        void UpdatePreview();
        Windows::UI::Color ColorFromPosition(double hue, double saturation, double value);

        Windows::UI::Color m_selectedColor{ 0, 0, 0, 0 };
        double m_opacity{ 1.0 };
        bool m_showAlpha{ false };

        Microsoft::UI::Xaml::Controls::Canvas m_colorWheel{ nullptr };
        Microsoft::UI::Xaml::Shapes::Ellipse m_selector{ nullptr };
        Microsoft::UI::Xaml::Controls::Border m_preview{ nullptr };
        Microsoft::UI::Xaml::Controls::Slider m_redSlider{ nullptr };
        Microsoft::UI::Xaml::Controls::Slider m_greenSlider{ nullptr };
        Microsoft::UI::Xaml::Controls::Slider m_blueSlider{ nullptr };
        Microsoft::UI::Xaml::Controls::TextBlock m_hexText{ nullptr };

        winrt::Windows::Foundation::EventHandler<Windows::UI::Color> m_colorChangedHandler;

        std::vector<Windows::UI::Color> m_palette;
    };
}
