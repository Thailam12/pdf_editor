#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Controls
{
    struct PDFCanvas : winrt::Microsoft::UI::Xaml::Controls::Control
    {
        PDFCanvas();

        void SetDocument(hstring const& filePath);
        void RenderPage(int pageIndex);
        void SetZoom(double zoomLevel);
        void SetPan(double offsetX, double offsetY);

        Microsoft::UI::Xaml::FrameworkElement Root() const { return m_root; }
        Microsoft::UI::Xaml::Controls::Grid ContainerGrid() const { return m_container; }

        // Input handling
        void OnPointerPressed(Windows::Foundation::IInspectable const& sender,
                              Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);
        void OnPointerReleased(Windows::Foundation::IInspectable const& sender,
                               Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);
        void OnPointerMoved(Windows::Foundation::IInspectable const& sender,
                            Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);
        void OnPointerWheelChanged(Windows::Foundation::IInspectable const& sender,
                                   Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);

        // Hit testing
        bool HitTest(double x, double y, std::wstring& hitResult);
        std::vector<Microsoft::UI::Xaml::Rect> GetSelectionRects() const;

    private:
        void InitializeD2D();
        void CreateSwapChain();
        void RenderFrame();
        void HandleZoom(double delta);
        void HandlePanStart(double x, double y);
        void HandlePanMove(double x, double y);
        void HandlePanEnd();

        Microsoft::UI::Xaml::Controls::Grid m_container{ nullptr };
        Microsoft::UI::Xaml::FrameworkElement m_root{ nullptr };

        winrt::com_ptr<ID2D1Factory1> m_d2dFactory;
        winrt::com_ptr<ID2D1Device> m_d2dDevice;
        winrt::com_ptr<ID2D1DeviceContext> m_d2dContext;
        winrt::com_ptr<IDXGISwapChain1> m_swapChain;
        winrt::com_ptr<ID2D1Bitmap1> m_targetBitmap;

        std::wstring m_documentPath;
        int m_currentPage{ 0 };
        double m_zoomLevel{ 1.0 };
        double m_panOffsetX{ 0.0 };
        double m_panOffsetY{ 0.0 };

        bool m_isPanning{ false };
        double m_panStartX{ 0.0 };
        double m_panStartY{ 0.0 };
        double m_panStartOffsetX{ 0.0 };
        double m_panStartOffsetY{ 0.0 };

        std::vector<Microsoft::UI::Xaml::Rect> m_selectionRects;

        float m_pageWidth{ 612.0f };
        float m_pageHeight{ 792.0f };
        float m_pageMargin{ 40.0f };
    };
}
