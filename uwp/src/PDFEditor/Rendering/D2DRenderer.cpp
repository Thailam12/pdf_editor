#include "pch.h"
#include "Rendering/D2DRenderer.h"

using namespace winrt;
using namespace Windows::UI;

namespace winrt::PDFEditor::Rendering
{
    D2DRenderer::D2DRenderer()
    {
    }

    D2DRenderer::~D2DRenderer()
    {
        Shutdown();
    }

    bool D2DRenderer::Initialize(HWND hwnd)
    {
        if (m_initialized) return true;

        m_hwnd = hwnd;
        HRESULT hr = D2D1CreateFactory(
            D2D1_FACTORY_TYPE_SINGLE_THREADED,
            __uuidof(ID2D1Factory1),
            m_factory.put_void());

        if (FAILED(hr))
        {
            OutputDebugStringW(L"[D2DRenderer] Failed to create factory\n");
            return false;
        }

        CreateDeviceResources();
        m_initialized = true;
        return true;
    }

    void D2DRenderer::Shutdown()
    {
        m_brushCache.clear();
        m_renderTarget = nullptr;
        m_context = nullptr;
        m_device = nullptr;
        m_factory = nullptr;
        m_initialized = false;
    }

    bool D2DRenderer::IsInitialized() const { return m_initialized; }

    void D2DRenderer::CreateDeviceResources()
    {
        if (!m_factory || !m_hwnd) return;

        RECT rc;
        GetClientRect(m_hwnd, &rc);

        D2D1_RENDER_TARGET_PROPERTIES rtProps = D2D1::RenderTargetProperties();
        D2D1_HWND_RENDER_TARGET_PROPERTIES hwndProps = D2D1::HwndRenderTargetProperties(
            m_hwnd,
            D2D1::SizeU(rc.right - rc.left, rc.bottom - rc.top));

        HRESULT hr = m_factory->CreateHwndRenderTarget(rtProps, hwndProps, m_renderTarget.put());
        if (FAILED(hr))
        {
            OutputDebugStringW(L"[D2DRenderer] Failed to create render target\n");
            return;
        }
    }

    void D2DRenderer::CreateBrushes()
    {
    }

    void D2DRenderer::BeginDraw()
    {
        if (m_renderTarget)
        {
            m_renderTarget->BeginDraw();
        }
    }

    void D2DRenderer::EndDraw()
    {
        if (m_renderTarget)
        {
            HRESULT hr = m_renderTarget->EndDraw();
            if (hr == D2DERR_RECREATE_TARGET)
            {
                m_renderTarget = nullptr;
                CreateDeviceResources();
            }
        }
    }

    void D2DRenderer::Clear(Color clearColor)
    {
        if (m_renderTarget)
        {
            m_renderTarget->Clear(D2D1::ColorF(
                clearColor.R / 255.0f,
                clearColor.G / 255.0f,
                clearColor.B / 255.0f,
                clearColor.A / 255.0f));
        }
    }

    void D2DRenderer::DrawRectangle(float x, float y, float width, float height,
                                      Color fillColor, float strokeWidth, Color strokeColor)
    {
        if (!m_renderTarget) return;

        winrt::com_ptr<ID2D1SolidColorBrush> fillBrush;
        m_renderTarget->CreateSolidColorBrush(
            D2D1::ColorF(fillColor.R / 255.0f, fillColor.G / 255.0f,
                         fillColor.B / 255.0f, fillColor.A / 255.0f),
            fillBrush.put());

        m_renderTarget->FillRectangle(
            D2D1::RectF(x, y, x + width, y + height),
            fillBrush.get());

        if (strokeWidth > 0 && strokeColor.A > 0)
        {
            winrt::com_ptr<ID2D1SolidColorBrush> strokeBrush;
            m_renderTarget->CreateSolidColorBrush(
                D2D1::ColorF(strokeColor.R / 255.0f, strokeColor.G / 255.0f,
                             strokeColor.B / 255.0f, strokeColor.A / 255.0f),
                strokeBrush.put());

            m_renderTarget->DrawRectangle(
                D2D1::RectF(x, y, x + width, y + height),
                strokeBrush.get(), strokeWidth);
        }
    }

    void D2DRenderer::DrawRoundedRectangle(float x, float y, float width, float height,
                                             float radiusX, float radiusY, Color fillColor)
    {
        if (!m_renderTarget) return;

        winrt::com_ptr<ID2D1SolidColorBrush> brush;
        m_renderTarget->CreateSolidColorBrush(
            D2D1::ColorF(fillColor.R / 255.0f, fillColor.G / 255.0f,
                         fillColor.B / 255.0f, fillColor.A / 255.0f),
            brush.put());

        m_renderTarget->FillRoundedRectangle(
            D2D1::RoundedRect(D2D1::RectF(x, y, x + width, y + height), radiusX, radiusY),
            brush.get());
    }

    void D2DRenderer::DrawEllipse(float centerX, float centerY, float radiusX, float radiusY, Color fillColor)
    {
        if (!m_renderTarget) return;

        winrt::com_ptr<ID2D1SolidColorBrush> brush;
        m_renderTarget->CreateSolidColorBrush(
            D2D1::ColorF(fillColor.R / 255.0f, fillColor.G / 255.0f,
                         fillColor.B / 255.0f, fillColor.A / 255.0f),
            brush.put());

        m_renderTarget->FillEllipse(
            D2D1::Ellipse(D2D1::Point2F(centerX, centerY), radiusX, radiusY),
            brush.get());
    }

    void D2DRenderer::DrawLine(float x1, float y1, float x2, float y2, Color color, float strokeWidth)
    {
        if (!m_renderTarget) return;

        winrt::com_ptr<ID2D1SolidColorBrush> brush;
        m_renderTarget->CreateSolidColorBrush(
            D2D1::ColorF(color.R / 255.0f, color.G / 255.0f,
                         color.B / 255.0f, color.A / 255.0f),
            brush.put());

        m_renderTarget->DrawLine(
            D2D1::Point2F(x1, y1),
            D2D1::Point2F(x2, y2),
            brush.get(), strokeWidth);
    }

    void D2DRenderer::DrawText(hstring const& text, float x, float y, float maxWidth,
                                 Color color, float fontSize, hstring const& fontFamily)
    {
        if (!m_renderTarget) return;

        winrt::com_ptr<IDWriteFactory> dwriteFactory;
        DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED,
            __uuidof(IDWriteFactory), dwriteFactory.put_void());

        winrt::com_ptr<IDWriteTextFormat> textFormat;
        dwriteFactory->CreateTextFormat(
            fontFamily.c_str(), nullptr,
            DWRITE_FONT_WEIGHT_NORMAL,
            DWRITE_FONT_STYLE_NORMAL,
            DWRITE_FONT_STRETCH_NORMAL,
            fontSize * (m_dpi / 96.0f),
            L"",
            textFormat.put());

        winrt::com_ptr<ID2D1SolidColorBrush> brush;
        m_renderTarget->CreateSolidColorBrush(
            D2D1::ColorF(color.R / 255.0f, color.G / 255.0f,
                         color.B / 255.0f, color.A / 255.0f),
            brush.put());

        m_renderTarget->DrawText(
            text.c_str(),
            static_cast<UINT32>(text.length()),
            textFormat.get(),
            D2D1::RectF(x, y, x + maxWidth, y + fontSize * 2),
            brush.get());
    }

    void D2DRenderer::DrawBitmap(void* bitmapData, uint32_t width, uint32_t height,
                                   float x, float y, float destWidth, float destHeight)
    {
        if (!m_renderTarget || !bitmapData) return;

        D2D1_BITMAP_PROPERTIES bmpProps = D2D1::BitmapProperties(
            D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_PREMULTIPLIED));

        winrt::com_ptr<ID2D1Bitmap> bitmap;
        m_renderTarget->CreateBitmap(
            D2D1::SizeU(width, height),
            bitmapData,
            width * 4,
            bmpProps,
            bitmap.put());

        if (bitmap)
        {
            m_renderTarget->DrawBitmap(
                bitmap.get(),
                D2D1::RectF(x, y, x + destWidth, y + destHeight));
        }
    }

    void D2DRenderer::DrawPolygon(std::vector<std::pair<float, float>> const& points, Color fillColor)
    {
        if (!m_renderTarget || points.size() < 3) return;

        winrt::com_ptr<ID2D1SolidColorBrush> brush;
        m_renderTarget->CreateSolidColorBrush(
            D2D1::ColorF(fillColor.R / 255.0f, fillColor.G / 255.0f,
                         fillColor.B / 255.0f, fillColor.A / 255.0f),
            brush.put());

        std::vector<D2D1_POINT_2F> d2dPoints;
        for (auto const& [x, y] : points)
        {
            d2dPoints.push_back(D2D1::Point2F(x, y));
        }

        winrt::com_ptr<ID2D1GeometrySink> sink;
        winrt::com_ptr<ID2D1PathGeometry> path;
        m_factory->CreatePathGeometry(path.put());
        path->Open(sink.put());

        sink->BeginFigure(d2dPoints[0], D2D1_FIGURE_BEGIN_FILLED);
        sink->AddLines(d2dPoints.data() + 1, static_cast<UINT32>(d2dPoints.size() - 1));
        sink->EndFigure(D2D1_FIGURE_END_CLOSED);
        sink->Close();

        m_renderTarget->FillGeometry(path.get(), brush.get());
    }

    void D2DRenderer::PushClip(float x, float y, float width, float height)
    {
        if (m_renderTarget)
        {
            m_renderTarget->PushAxisAlignedClip(
                D2D1::RectF(x, y, x + width, y + height),
                D2D1_ANTIALIAS_MODE_PER_PRIMITIVE);
        }
    }

    void D2DRenderer::PopClip()
    {
        if (m_renderTarget)
        {
            m_renderTarget->PopAxisAlignedClip();
        }
    }

    void D2DRenderer::PushTransform(float scaleX, float scaleY, float offsetX, float offsetY)
    {
        if (m_renderTarget)
        {
            m_renderTarget->SetTransform(
                D2D1::Matrix3x2F::Scale(scaleX, scaleY) *
                D2D1::Matrix3x2F::Translation(offsetX, offsetY));
        }
    }

    void D2DRenderer::PopTransform()
    {
        if (m_renderTarget)
        {
            m_renderTarget->SetTransform(D2D1::Matrix3x2F::Identity());
        }
    }

    void D2DRenderer::SetAntiAlias(bool enabled)
    {
        if (m_renderTarget)
        {
            m_renderTarget->SetTextAntialiasMode(
                enabled ? D2D1_TEXT_ANTIALIAS_MODE_GRAYSCALE : D2D1_TEXT_ANTIALIAS_MODE_ALIASED);
        }
    }

    void D2DRenderer::SetRenderingQuality(bool highQuality)
    {
        if (m_renderTarget)
        {
            m_renderTarget->SetAntialiasMode(
                highQuality ? D2D1_ANTIALIAS_MODE_PER_PRIMITIVE : D2D1_ANTIALIAS_MODE_ALIASED);
        }
    }

    float D2DRenderer::GetDPI() const { return m_dpi; }
    void D2DRenderer::SetDPI(float dpi) { m_dpi = dpi; }
}
