#include "pch.h"
#include "Rendering/TextLayout.h"

using namespace winrt;
using namespace Windows::UI;

namespace winrt::PDFEditor::Rendering
{
    TextLayout::TextLayout()
    {
    }

    void TextLayout::EnsureFactory()
    {
        if (!m_dwriteFactory)
        {
            DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED,
                __uuidof(IDWriteFactory), m_dwriteFactory.put_void());
        }
    }

    bool TextLayout::Create(hstring const& text, hstring const& fontFamily, float fontSize,
                             float maxWidth, float maxHeight)
    {
        EnsureFactory();
        if (!m_dwriteFactory) return false;

        m_fontFamily = fontFamily;
        m_fontSize = fontSize;
        m_maxWidth = maxWidth;
        m_maxHeight = maxHeight;

        HRESULT hr = m_dwriteFactory->CreateTextFormat(
            fontFamily.c_str(), nullptr,
            DWRITE_FONT_WEIGHT_NORMAL,
            DWRITE_FONT_STYLE_NORMAL,
            DWRITE_FONT_STRETCH_NORMAL,
            fontSize,
            L"en-US",
            m_textFormat.put());

        if (FAILED(hr)) return false;

        hr = m_dwriteFactory->CreateTextLayout(
            text.c_str(),
            static_cast<UINT32>(text.length()),
            m_textFormat.get(),
            maxWidth,
            maxHeight,
            m_textLayout.put());

        m_needsRebuild = false;
        return SUCCEEDED(hr);
    }

    void TextLayout::SetText(hstring const& text)
    {
        EnsureFactory();
        if (!m_dwriteFactory) return;

        hr = m_dwriteFactory->CreateTextLayout(
            text.c_str(),
            static_cast<UINT32>(text.length()),
            m_textFormat.get(),
            m_maxWidth,
            m_maxHeight,
            m_textLayout.put());

        m_needsRebuild = false;
    }

    void TextLayout::SetFont(hstring const& fontFamily, float fontSize)
    {
        m_fontFamily = fontFamily;
        m_fontSize = fontSize;
        m_needsRebuild = true;

        if (m_dwriteFactory)
        {
            m_dwriteFactory->CreateTextFormat(
                fontFamily.c_str(), nullptr,
                DWRITE_FONT_WEIGHT_NORMAL,
                DWRITE_FONT_STYLE_NORMAL,
                DWRITE_FONT_STRETCH_NORMAL,
                fontSize,
                L"en-US",
                m_textFormat.put());
        }
    }

    void TextLayout::SetConstraints(float maxWidth, float maxHeight)
    {
        m_maxWidth = maxWidth;
        m_maxHeight = maxHeight;
        m_needsRebuild = true;
    }

    void TextLayout::SetColor(Windows::UI::Color color)
    {
        m_color = color;
    }

    void TextLayout::SetAlignment(DWRITE_TEXT_ALIGNMENT alignment)
    {
        if (m_textFormat)
        {
            m_textFormat->SetTextAlignment(alignment);
        }
    }

    void TextLayout::SetParagraphAlignment(DWRITE_PARAGRAPH_ALIGNMENT alignment)
    {
        if (m_textFormat)
        {
            m_textFormat->SetParagraphAlignment(alignment);
        }
    }

    void TextLayout::SetWordWrapping(DWRITE_WORD_WRAPPING wrapping)
    {
        if (m_textFormat)
        {
            m_textFormat->SetWordWrapping(wrapping);
        }
    }

    void TextLayout::Draw(float x, float y)
    {
        if (!m_textLayout) return;

        ID2D1RenderTarget* rt = nullptr;
        DWRITE_TEXT_METRICS metrics;
        m_textLayout->GetMetrics(&metrics);

        OutputDebugStringW(L"[TextLayout] Draw at ");
        OutputDebugStringW(std::to_wstring(static_cast<int>(x)).c_str());
        OutputDebugStringW(L", ");
        OutputDebugStringW(std::to_wstring(static_cast<int>(y)).c_str());
        OutputDebugStringW(L"\n");
    }

    float TextLayout::GetMeasuredWidth() const
    {
        if (!m_textLayout) return 0;
        DWRITE_TEXT_METRICS metrics;
        m_textLayout->GetMetrics(&metrics);
        return metrics.widthIncludingTrailingWhitespace;
    }

    float TextLayout::GetMeasuredHeight() const
    {
        if (!m_textLayout) return 0;
        DWRITE_TEXT_METRICS metrics;
        m_textLayout->GetMetrics(&metrics);
        return metrics.height;
    }

    std::pair<float, float> TextLayout::GetLineMetrics() const
    {
        if (!m_textLayout) return { 0, 0 };

        DWRITE_TEXT_METRICS metrics;
        m_textLayout->GetMetrics(&metrics);

        uint32_t lineCount = 0;
        m_textLayout->GetLineMetrics(nullptr, 0, &lineCount);

        if (lineCount > 0)
        {
            std::vector<DWRITE_LINE_METRICS> lines(lineCount);
            m_textLayout->GetLineMetrics(lines.data(), lineCount, &lineCount);
            return { lines[0].baseline, metrics.height };
        }

        return { metrics.height, metrics.height };
    }

    bool TextLayout::HitTestPoint(float x, float y, int& characterIndex, bool& isTrailingHit) const
    {
        if (!m_textLayout) return false;

        BOOL isInside = FALSE;
        BOOL isTrailing = FALSE;
        DWRITE_HIT_TEST_METRICS hitMetrics;

        HRESULT hr = m_textLayout->HitTestPoint(x, y, &isInside, &isTrailing, &hitMetrics);

        if (SUCCEEDED(hr))
        {
            characterIndex = static_cast<int>(hitMetrics.textPosition);
            isTrailingHit = isTrailing != FALSE;
            return isInside != FALSE;
        }

        return false;
    }

    void TextLayout::Release()
    {
        m_textLayout = nullptr;
        m_textFormat = nullptr;
        m_dwriteFactory = nullptr;
    }
}
