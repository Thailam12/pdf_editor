#include "pch.h"
#include "Controls/PDFCanvas.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;
using namespace Microsoft::UI::Xaml::Input;

namespace winrt::PDFEditor::Controls
{
    PDFCanvas::PDFCanvas()
    {
        m_container = Grid();
        m_container.Background(Microsoft::UI::Xaml::Media::Brushes::White());

        m_container.PointerPressed([this](auto const& sender, auto const& args)
        {
            OnPointerPressed(sender, args);
        });
        m_container.PointerReleased([this](auto const& sender, auto const& args)
        {
            OnPointerReleased(sender, args);
        });
        m_container.PointerMoved([this](auto const& sender, auto const& args)
        {
            OnPointerMoved(sender, args);
        });
        m_container.PointerWheelChanged([this](auto const& sender, auto const& args)
        {
            OnPointerWheelChanged(sender, args);
        });

        m_root = m_container;
        InitializeD2D();
    }

    void PDFCanvas::InitializeD2D()
    {
        HRESULT hr = D2D1CreateFactory(
            D2D1_FACTORY_TYPE_SINGLE_THREADED,
            __uuidof(ID2D1Factory1),
            m_d2dFactory.put_void());

        if (FAILED(hr))
        {
            OutputDebugStringW(L"[PDFCanvas] Failed to create D2D factory\n");
            return;
        }

        winrt::com_ptr<IDXGIDevice> dxgiDevice;
        winrt::com_ptr<ID3D11Device> d3dDevice;
        D3D_FEATURE_LEVEL featureLevels[] = { D3D_FEATURE_LEVEL_11_1 };
        D3D_FEATURE_LEVEL featureLevel;

        hr = D3D11CreateDevice(
            nullptr,
            D3D_DRIVER_TYPE_HARDWARE,
            nullptr,
            D3D11_CREATE_DEVICE_BGRA_SUPPORT,
            featureLevels,
            1,
            D3D11_SDK_VERSION,
            d3dDevice.put(),
            &featureLevel,
            nullptr);

        if (FAILED(hr))
        {
            OutputDebugStringW(L"[PDFCanvas] Failed to create D3D device\n");
            return;
        }

        dxgiDevice = d3dDevice.as<IDXGIDevice>();
        hr = m_d2dFactory->CreateDevice(dxgiDevice.get(), m_d2dDevice.put());
        if (FAILED(hr))
        {
            OutputDebugStringW(L"[PDFCanvas] Failed to create D2D device\n");
            return;
        }

        hr = m_d2dDevice->CreateDeviceContext(
            D2D1_DEVICE_CONTEXT_OPTIONS_NONE,
            m_d2dContext.put());

        if (FAILED(hr))
        {
            OutputDebugStringW(L"[PDFCanvas] Failed to create D2D device context\n");
            return;
        }

        CreateSwapChain();
        OutputDebugStringW(L"[PDFCanvas] D2D initialized successfully\n");
    }

    void PDFCanvas::CreateSwapChain()
    {
        if (!m_d2dFactory || !m_d2dDevice) return;

        winrt::com_ptr<IDXGIDevice> dxgiDevice = m_d2dDevice.as<IDXGIDevice>();
        winrt::com_ptr<IDXGIAdapter> adapter;
        HRESULT hr = dxgiDevice->GetAdapter(adapter.put());
        if (FAILED(hr)) return;

        winrt::com_ptr<IDXGIFactory2> dxgiFactory;
        hr = adapter->GetParent(__uuidof(IDXGIFactory2), dxgiFactory.put_void());
        if (FAILED(hr)) return;

        DXGI_SWAP_CHAIN_DESC1 desc{};
        desc.Width = 1;
        desc.Height = 1;
        desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        desc.Stereo = FALSE;
        desc.SampleDesc.Count = 1;
        desc.SampleDesc.Quality = 0;
        desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
        desc.BufferCount = 2;
        desc.Scaling = DXGI_SCALING_STRETCH;
        desc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD;
        desc.AlphaMode = DXGI_ALPHA_MODE_IGNORE;

        hr = dxgiFactory->CreateSwapChainForHwnd(
            nullptr,
            GetActiveWindow(),
            &desc,
            nullptr,
            nullptr,
            m_swapChain.put());

        if (FAILED(hr))
        {
            OutputDebugStringW(L"[PDFCanvas] Failed to create swap chain\n");
        }
    }

    void PDFCanvas::RenderFrame()
    {
        if (!m_d2dContext || !m_swapChain) return;

        m_d2dContext->SetTarget(nullptr);
        m_d2dContext->Flush();

        HRESULT hr;
        winrt::com_ptr<IDXGISurface> backBuffer;
        hr = m_swapChain->GetBuffer(0, __uuidof(IDXGISurface), backBuffer.put_void());
        if (FAILED(hr)) return;

        D2D1_BITMAP_PROPERTIES1 bmpProps = D2D1::BitmapProperties1(
            D2D1_BITMAP_OPTIONS_TARGET | D2D1_BITMAP_OPTIONS_CANNOT_DRAW,
            D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_PREMULTIPLIED));

        hr = m_d2dContext->CreateBitmapFromDxgiSurface(
            backBuffer.get(), &bmpProps, m_targetBitmap.put());

        if (FAILED(hr)) return;

        m_d2dContext->SetTarget(m_targetBitmap.get());
        m_d2dContext->BeginDraw();

        m_d2dContext->Clear(D2D1::ColorF(D2D1::ColorF::White));

        auto scale = static_cast<float>(m_zoomLevel);
        auto offsetX = static_cast<float>(m_panOffsetX);
        auto offsetY = static_cast<float>(m_panOffsetY);

        D2D1_RECT_F pageRect = D2D1::RectF(
            offsetX + m_pageMargin,
            offsetY + m_pageMargin,
            offsetX + m_pageMargin + m_pageWidth * scale,
            offsetY + m_pageMargin + m_pageHeight * scale);

        winrt::com_ptr<ID2D1SolidColorBrush> shadowBrush;
        m_d2dContext->CreateSolidColorBrush(
            D2D1::ColorF(0.0f, 0.0f, 0.0f, 0.1f), shadowBrush.put());

        m_d2dContext->FillRectangle(
            D2D1::RectF(pageRect.left + 3, pageRect.top + 3,
                        pageRect.right + 3, pageRect.bottom + 3),
            shadowBrush.get());

        winrt::com_ptr<ID2D1SolidColorBrush> pageBrush;
        m_d2dContext->CreateSolidColorBrush(
            D2D1::ColorF(D2D1::ColorF::White), pageBrush.get());
        m_d2dContext->FillRectangle(pageRect, pageBrush.get());

        winrt::com_ptr<ID2D1SolidColorBrush> borderBrush;
        m_d2dContext->CreateSolidColorBrush(
            D2D1::ColorF(0.8f, 0.8f, 0.8f), borderBrush.get());
        m_d2dContext->DrawRectangle(pageRect, borderBrush.get(), 1.0f);

        winrt::com_ptr<ID2D1SolidColorBrush> textBrush;
        m_d2dContext->CreateSolidColorBrush(
            D2D1::ColorF(0.4f, 0.4f, 0.4f), textBrush.get());

        winrt::com_ptr<IDWriteFactory> dwriteFactory;
        DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED,
            __uuidof(IDWriteFactory), dwriteFactory.put_void());

        winrt::com_ptr<IDWriteTextFormat> textFormat;
        dwriteFactory->CreateTextFormat(
            L"Segoe UI", nullptr,
            DWRITE_FONT_WEIGHT_NORMAL,
            DWRITE_FONT_STYLE_NORMAL,
            DWRITE_FONT_STRETCH_NORMAL,
            12.0f * scale,
            L"",
            textFormat.put());

        textFormat->SetTextAlignment(DWRITE_TEXT_ALIGNMENT_CENTER);
        textFormat->SetParagraphAlignment(DWRITE_PARAGRAPH_ALIGNMENT_CENTER);

        auto label = L"Page " + std::to_wstring(m_currentPage + 1);
        m_d2dContext->DrawText(
            label.c_str(),
            static_cast<UINT32>(label.length()),
            textFormat.get(),
            D2D1::RectF(pageRect.left, pageRect.top + 40 * scale,
                        pageRect.right, pageRect.top + 60 * scale),
            textBrush.get());

        hr = m_d2dContext->EndDraw();
        if (hr == D2DERR_RECREATE_TARGET)
        {
            m_d2dContext = nullptr;
            m_targetBitmap = nullptr;
            m_swapChain = nullptr;
            InitializeD2D();
        }
    }

    void PDFCanvas::SetDocument(hstring const& filePath)
    {
        m_documentPath = std::wstring(filePath);
        m_currentPage = 0;
        m_zoomLevel = 1.0;
        m_panOffsetX = 0.0;
        m_panOffsetY = 0.0;
        RenderFrame();
    }

    void PDFCanvas::RenderPage(int pageIndex)
    {
        m_currentPage = pageIndex;
        RenderFrame();
    }

    void PDFCanvas::SetZoom(double zoomLevel)
    {
        m_zoomLevel = std::clamp(zoomLevel, 0.1, 10.0);
        RenderFrame();
    }

    void PDFCanvas::SetPan(double offsetX, double offsetY)
    {
        m_panOffsetX = offsetX;
        m_panOffsetY = offsetY;
        RenderFrame();
    }

    void PDFCanvas::OnPointerPressed(IInspectable const&, PointerRoutedEventArgs const& args)
    {
        auto props = args.GetCurrentPoint(nullptr).Properties();
        if (props.IsXButton1Pressed())
        {
            m_isPanning = true;
            auto point = args.GetCurrentPoint(nullptr).Position();
            m_panStartX = point.X;
            m_panStartY = point.Y;
            m_panStartOffsetX = m_panOffsetX;
            m_panStartOffsetY = m_panOffsetY;
            args.Handled(true);
        }
    }

    void PDFCanvas::OnPointerReleased(IInspectable const&, PointerRoutedEventArgs const&)
    {
        HandlePanEnd();
    }

    void PDFCanvas::OnPointerMoved(IInspectable const&, PointerRoutedEventArgs const& args)
    {
        if (m_isPanning)
        {
            auto point = args.GetCurrentPoint(nullptr).Position();
            HandlePanMove(point.X, point.Y);
            args.Handled(true);
        }
    }

    void PDFCanvas::OnPointerWheelChanged(IInspectable const&, PointerRoutedEventArgs const& args)
    {
        auto delta = args.GetCurrentPoint(nullptr).Properties().MouseWheelDelta();
        HandleZoom(delta > 0 ? 1.1 : 0.9);
        args.Handled(true);
    }

    bool PDFCanvas::HitTest(double x, double y, std::wstring& hitResult)
    {
        auto scale = static_cast<float>(m_zoomLevel);
        auto left = static_cast<float>(m_panOffsetX + m_pageMargin);
        auto top = static_cast<float>(m_panOffsetY + m_pageMargin);
        auto right = left + m_pageWidth * scale;
        auto bottom = top + m_pageHeight * scale;

        if (x >= left && x <= right && y >= top && y <= bottom)
        {
            auto pdfX = (x - left) / scale;
            auto pdfY = (y - top) / scale;
            hitResult = L"page:" + std::to_wstring(m_currentPage) +
                        L";x:" + std::to_wstring(pdfX) +
                        L";y:" + std::to_wstring(pdfY);
            return true;
        }
        return false;
    }

    std::vector<Rect> PDFCanvas::GetSelectionRects() const
    {
        return m_selectionRects;
    }

    void PDFCanvas::HandleZoom(double factor)
    {
        m_zoomLevel = std::clamp(m_zoomLevel * factor, 0.1, 10.0);
        RenderFrame();
    }

    void PDFCanvas::HandlePanStart(double x, double y)
    {
        m_isPanning = true;
        m_panStartX = x;
        m_panStartY = y;
        m_panStartOffsetX = m_panOffsetX;
        m_panStartOffsetY = m_panOffsetY;
    }

    void PDFCanvas::HandlePanMove(double x, double y)
    {
        if (!m_isPanning) return;
        m_panOffsetX = m_panStartOffsetX + (x - m_panStartX);
        m_panOffsetY = m_panStartOffsetY + (y - m_panStartY);
        RenderFrame();
    }

    void PDFCanvas::HandlePanEnd()
    {
        m_isPanning = false;
    }
}
