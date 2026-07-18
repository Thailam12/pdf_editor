#include "pch.h"
#include "Controls/ZoomControl.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::PDFEditor::Controls
{
    ZoomControl::ZoomControl()
    {
        m_slider = Microsoft::UI::Xaml::Controls::Slider();
        m_slider.Minimum(m_minZoom);
        m_slider.Maximum(m_maxZoom);
        m_slider.Value(m_zoomLevel);
        m_slider.Width(120);
        m_slider.HorizontalAlignment(HorizontalAlignment::Center);

        m_slider.ValueChanged([this](auto const& sender, auto const& args)
        {
            if (m_zoomLevel != args.NewValue())
            {
                m_zoomLevel = args.NewValue();
                UpdateDisplay();
                if (m_zoomChangedHandler)
                {
                    m_zoomChangedHandler(nullptr, m_zoomLevel);
                }
            }
        });

        m_label = Microsoft::UI::Xaml::Controls::TextBlock();
        m_label.Text(L"100%");
        m_label.VerticalAlignment(VerticalAlignment::Center);
        m_label.Margin(ThicknessHelper::FromLengths(8, 0, 0, 0));
        m_label.Style(Application::Current().FindResource(L"CaptionTextBlockStyle").as<Style>());

        m_zoomInBtn = Microsoft::UI::Xaml::Controls::Button();
        m_zoomInBtn.Content(winrt::box_value(L"+"));
        m_zoomInBtn.Width(28);
        m_zoomInBtn.Height(28);
        m_zoomInBtn.Click([this](auto const&, auto const&)
        {
            ZoomLevel(std::min(m_zoomLevel + 10.0, m_maxZoom));
        });

        m_zoomOutBtn = Microsoft::UI::Xaml::Controls::Button();
        m_zoomOutBtn.Content(winrt::box_value(L"-"));
        m_zoomOutBtn.Width(28);
        m_zoomOutBtn.Height(28);
        m_zoomOutBtn.Click([this](auto const&, auto const&)
        {
            ZoomLevel(std::max(m_zoomLevel - 10.0, m_minZoom));
        });

        m_fitBtn = Microsoft::UI::Xaml::Controls::Button();
        m_fitBtn.Content(winrt::box_value(L"Fit"));
        m_fitBtn.Padding(ThicknessHelper::FromLengths(8, 2, 8, 2));
    }

    void ZoomControl::ZoomLevel(double value)
    {
        m_zoomLevel = std::clamp(value, m_minZoom, m_maxZoom);
        if (m_slider)
            m_slider().Value(m_zoomLevel);
        UpdateDisplay();

        if (m_zoomChangedHandler)
        {
            m_zoomChangedHandler(nullptr, m_zoomLevel);
        }
    }

    void ZoomControl::ZoomToFit(double pageWidth, double pageHeight,
                                 double viewportWidth, double viewportHeight)
    {
        auto scaleX = (viewportWidth - 80.0) / pageWidth;
        auto scaleY = (viewportHeight - 80.0) / pageHeight;
        ZoomLevel(std::min(scaleX, scaleY) * 100.0);
    }

    void ZoomControl::ZoomToWidth(double pageWidth, double viewportWidth)
    {
        ZoomLevel(((viewportWidth - 80.0) / pageWidth) * 100.0);
    }

    void ZoomControl::UpdateDisplay()
    {
        if (m_label)
        {
            m_label().Text(winrt::to_hstring(static_cast<int>(m_zoomLevel)) + L"%");
        }
        if (m_slider)
        {
            m_slider().Value(m_zoomLevel);
        }
    }

    event_token ZoomControl::ZoomChanged(Windows::Foundation::EventHandler<double> const& handler)
    {
        return m_zoomChangedHandler.add(handler);
    }

    void ZoomControl::ZoomChanged(event_token const& token) noexcept
    {
        m_zoomChangedHandler.remove(token);
    }
}
