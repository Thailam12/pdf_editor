#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Controls
{
    struct ZoomControl : winrt::Microsoft::UI::Xaml::Controls::Control
    {
        ZoomControl();

        double ZoomLevel() const { return m_zoomLevel; }
        void ZoomLevel(double value);
        void ZoomToFit(double pageWidth, double pageHeight, double viewportWidth, double viewportHeight);
        void ZoomToWidth(double pageWidth, double viewportWidth);

        winrt::event_token ZoomChanged(winrt::Windows::Foundation::EventHandler<double> const& handler);
        void ZoomChanged(winrt::event_token const& token) noexcept;

    private:
        void UpdateDisplay();

        Microsoft::UI::Xaml::Controls::Slider m_slider{ nullptr };
        Microsoft::UI::Xaml::Controls::TextBlock m_label{ nullptr };
        Microsoft::UI::Xaml::Controls::Button m_zoomInBtn{ nullptr };
        Microsoft::UI::Xaml::Controls::Button m_zoomOutBtn{ nullptr };
        Microsoft::UI::Xaml::Controls::Button m_fitBtn{ nullptr };
        Microsoft::UI::Xaml::Controls::Button m_widthBtn{ nullptr };

        double m_zoomLevel{ 100.0 };
        double m_minZoom{ 10.0 };
        double m_maxZoom{ 500.0 };

        winrt::Windows::Foundation::EventHandler<double> m_zoomChangedHandler;
    };
}
