#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Rendering
{
    struct TextLayout
    {
        TextLayout();

        bool Create(hstring const& text, hstring const& fontFamily, float fontSize,
                   float maxWidth, float maxHeight);
        void SetText(hstring const& text);
        void SetFont(hstring const& fontFamily, float fontSize);
        void SetConstraints(float maxWidth, float maxHeight);
        void SetColor(Windows::UI::Color color);
        void SetAlignment(DWRITE_TEXT_ALIGNMENT alignment);
        void SetParagraphAlignment(DWRITE_PARAGRAPH_ALIGNMENT alignment);
        void SetWordWrapping(DWRITE_WORD_WRAPPING wrapping);

        void Draw(float x, float y);
        float GetMeasuredWidth() const;
        float GetMeasuredHeight() const;
        std::pair<float, float> GetLineMetrics() const;
        bool HitTestPoint(float x, float y, int& characterIndex, bool& isTrailingHit) const;

        void Release();

    private:
        void EnsureFactory();

        winrt::com_ptr<IDWriteFactory> m_dwriteFactory;
        winrt::com_ptr<IDWriteTextFormat> m_textFormat;
        winrt::com_ptr<IDWriteTextLayout> m_textLayout;
        Windows::UI::Color m_color{ 0, 0, 0, 0 };
        hstring m_fontFamily{ L"Segoe UI" };
        float m_fontSize{ 12.0f };
        float m_maxWidth{ 1000.0f };
        float m_maxHeight{ 1000.0f };
        bool m_needsRebuild{ true };
    };
}
