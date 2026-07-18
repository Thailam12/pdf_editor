#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Rendering
{
    struct D2DRenderer
    {
        D2DRenderer();
        ~D2DRenderer();

        bool Initialize(HWND hwnd);
        void Shutdown();
        bool IsInitialized() const;

        void BeginDraw();
        void EndDraw();
        void Clear(Windows::UI::Color clearColor);

        void DrawRectangle(float x, float y, float width, float height,
                          Windows::UI::Color fillColor, float strokeWidth = 1.0f,
                          Windows::UI::Color strokeColor = { 0, 0, 0, 0 });
        void DrawRoundedRectangle(float x, float y, float width, float height,
                                  float radiusX, float radiusY,
                                  Windows::UI::Color fillColor);
        void DrawEllipse(float centerX, float centerY, float radiusX, float radiusY,
                        Windows::UI::Color fillColor);
        void DrawLine(float x1, float y1, float x2, float y2,
                     Windows::UI::Color color, float strokeWidth = 1.0f);
        void DrawText(hstring const& text, float x, float y, float maxWidth,
                     Windows::UI::Color color, float fontSize = 12.0f,
                     hstring const& fontFamily = L"Segoe UI");
        void DrawBitmap(void* bitmapData, uint32_t width, uint32_t height,
                       float x, float y, float destWidth, float destHeight);
        void DrawPolygon(std::vector<std::pair<float, float>> const& points,
                        Windows::UI::Color fillColor);

        void PushClip(float x, float y, float width, float height);
        void PopClip();
        void PushTransform(float scaleX, float scaleY, float offsetX, float offsetY);
        void PopTransform();

        void SetAntiAlias(bool enabled);
        void SetRenderingQuality(bool highQuality);

        float GetDPI() const;
        void SetDPI(float dpi);

    private:
        void CreateDeviceResources();
        void CreateBrushes();

        HWND m_hwnd{ nullptr };
        bool m_initialized{ false };
        float m_dpi{ 96.0f };

        winrt::com_ptr<ID2D1Factory1> m_factory;
        winrt::com_ptr<ID2D1HwndRenderTarget> m_renderTarget;
        winrt::com_ptr<ID2D1Device> m_device;
        winrt::com_ptr<ID2D1DeviceContext> m_context;

        std::unordered_map<uint32_t, winrt::com_ptr<ID2D1Brush>> m_brushCache;
    };
}
