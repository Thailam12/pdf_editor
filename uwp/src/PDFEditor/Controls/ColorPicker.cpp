#include "pch.h"
#include "Controls/ColorPicker.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;
using namespace Microsoft::UI::Xaml::Media;

namespace winrt::PDFEditor::Controls
{
    ColorPicker::ColorPicker()
    {
        BuildUI();
    }

    void ColorPicker::BuildUI()
    {
        m_colorWheel = Canvas();
        m_colorWheel.Width(200);
        m_colorWheel.Height(200);
        m_colorWheel.HorizontalAlignment(HorizontalAlignment::Center);

        m_selector = Microsoft::UI::Xaml::Shapes::Ellipse();
        m_selector.Width(12);
        m_selector.Height(12);
        m_selector.Stroke(Brushes::White());
        m_selector.StrokeThickness(2);
        m_selector.Fill(Brushes::Black());
        m_selector.HorizontalAlignment(HorizontalAlignment::Left);
        m_selector.VerticalAlignment(VerticalAlignment::Top);
        Canvas::SetLeft(m_selector, 94);
        Canvas::SetTop(m_selector, 94);

        for (int y = 0; y < 200; y += 4)
        {
            for (int x = 0; x < 200; x += 4)
            {
                auto dx = x - 100.0;
                auto dy = y - 100.0;
                auto dist = std::sqrt(dx * dx + dy * dy);
                if (dist <= 95.0)
                {
                    auto hue = std::atan2(dy, dx) * 180.0 / 3.14159265;
                    if (hue < 0) hue += 360.0;
                    auto sat = dist / 95.0;
                    auto color = ColorFromPosition(hue, sat, 1.0);

                    auto pixel = Microsoft::UI::Xaml::Shapes::Rectangle();
                    pixel.Width(5);
                    pixel.Height(5);
                    pixel.Fill(SolidColorBrush(color));
                    Canvas::SetLeft(pixel, x);
                    Canvas::SetTop(pixel, y);
                    m_colorWheel.Children().Append(pixel);
                }
            }
        }

        m_colorWheel.Children().Append(m_selector);

        m_preview = Border();
        m_preview.Width(40);
        m_preview.Height(28);
        m_preview.CornerRadius(CornerRadiusHelper::FromCornerRadius(4));
        m_preview.Background(SolidColorBrush(m_selectedColor));
        m_preview.HorizontalAlignment(HorizontalAlignment::Center);

        m_hexText = TextBlock();
        m_hexText.Text(L"#000000");
        m_hexText.HorizontalAlignment(HorizontalAlignment::Center);
        m_hexText.Style(Application::Current().FindResource(L"CaptionTextBlockStyle").as<Style>());
        m_hexText.Margin(ThicknessHelper::FromLengths(0, 4, 0, 0));

        m_redSlider = Slider();
        m_redSlider.Minimum(0);
        m_redSlider.Maximum(255);
        m_redSlider.Value(m_selectedColor.R);
        m_redSlider.Width(180);
        m_redSlider.Header(winrt::box_value(L"R"));
        m_redSlider.ValueChanged([this](auto const&, auto const& args)
        {
            m_selectedColor.R = static_cast<uint8_t>(args.NewValue());
            UpdatePreview();
            if (m_colorChangedHandler)
                m_colorChangedHandler(nullptr, m_selectedColor);
        });

        m_greenSlider = Slider();
        m_greenSlider.Minimum(0);
        m_greenSlider.Maximum(255);
        m_greenSlider.Value(m_selectedColor.G);
        m_greenSlider.Width(180);
        m_greenSlider.Header(winrt::box_value(L"G"));
        m_greenSlider.ValueChanged([this](auto const&, auto const& args)
        {
            m_selectedColor.G = static_cast<uint8_t>(args.NewValue());
            UpdatePreview();
            if (m_colorChangedHandler)
                m_colorChangedHandler(nullptr, m_selectedColor);
        });

        m_blueSlider = Slider();
        m_blueSlider.Minimum(0);
        m_blueSlider.Maximum(255);
        m_blueSlider.Value(m_selectedColor.B);
        m_blueSlider.Width(180);
        m_blueSlider.Header(winrt::box_value(L"B"));
        m_blueSlider.ValueChanged([this](auto const&, auto const& args)
        {
            m_selectedColor.B = static_cast<uint8_t>(args.NewValue());
            UpdatePreview();
            if (m_colorChangedHandler)
                m_colorChangedHandler(nullptr, m_selectedColor);
        });

        m_colorWheel.PointerPressed([this](auto const& sender, auto const& args)
        {
            auto point = args.GetCurrentPoint(nullptr).Position();
            auto dx = point.X - 100.0;
            auto dy = point.Y - 100.0;
            auto dist = std::sqrt(dx * dx + dy * dy);
            if (dist <= 95.0)
            {
                auto hue = std::atan2(dy, dx) * 180.0 / 3.14159265;
                if (hue < 0) hue += 360.0;
                auto sat = dist / 95.0;
                m_selectedColor = ColorFromPosition(hue, sat, 1.0);

                if (m_redSlider) m_redSlider().Value(m_selectedColor.R);
                if (m_greenSlider) m_greenSlider().Value(m_selectedColor.G);
                if (m_blueSlider) m_blueSlider().Value(m_selectedColor.B);

                Canvas::SetLeft(m_selector, point.X - 6);
                Canvas::SetTop(m_selector, point.Y - 6);

                UpdatePreview();
                if (m_colorChangedHandler)
                    m_colorChangedHandler(nullptr, m_selectedColor);
            }
        });
    }

    void ColorPicker::SelectedColor(Windows::UI::Color value)
    {
        m_selectedColor = value;
        if (m_redSlider) m_redSlider().Value(value.R);
        if (m_greenSlider) m_greenSlider().Value(value.G);
        if (m_blueSlider) m_blueSlider().Value(value.B);
        UpdatePreview();
    }

    void ColorPicker::Opacity(double value)
    {
        m_opacity = std::clamp(value, 0.0, 1.0);
        UpdatePreview();
    }

    void ColorPicker::ShowAlpha(bool value)
    {
        m_showAlpha = value;
    }

    void ColorPicker::UpdatePreview()
    {
        if (m_preview)
        {
            m_preview().Background(SolidColorBrush(m_selectedColor));
        }
        if (m_hexText)
        {
            wchar_t hex[8];
            swprintf_s(hex, L"#%02X%02X%02X", m_selectedColor.R, m_selectedColor.G, m_selectedColor.B);
            m_hexText().Text(hex);
        }
    }

    Windows::UI::Color ColorPicker::ColorFromPosition(double hue, double saturation, double value)
    {
        auto h = hue / 60.0;
        auto c = value * saturation;
        auto x = c * (1.0 - std::abs(std::fmod(h, 2.0) - 1.0));
        auto m = value - c;

        double r = 0, g = 0, b = 0;
        if (h < 1) { r = c; g = x; b = 0; }
        else if (h < 2) { r = x; g = c; b = 0; }
        else if (h < 3) { r = 0; g = c; b = x; }
        else if (h < 4) { r = 0; g = x; b = c; }
        else if (h < 5) { r = x; g = 0; b = c; }
        else { r = c; g = 0; b = x; }

        return Windows::UI::ColorHelper::FromArgb(
            255,
            static_cast<uint8_t>((r + m) * 255),
            static_cast<uint8_t>((g + m) * 255),
            static_cast<uint8_t>((b + m) * 255));
    }

    event_token ColorPicker::ColorChanged(Windows::Foundation::EventHandler<Windows::UI::Color> const& handler)
    {
        return m_colorChangedHandler.add(handler);
    }

    void ColorPicker::ColorChanged(event_token const& token) noexcept
    {
        m_colorChangedHandler.remove(token);
    }
}
