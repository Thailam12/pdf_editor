#pragma once

#include "Views/EditorView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct EditorView : EditorViewT<EditorView>
    {
        EditorView();

        double ZoomLevel();
        void ZoomLevel(double value);
        uint32_t CurrentPage();
        void CurrentPage(uint32_t value);
        uint32_t TotalPages();
        void TotalPages(uint32_t value);
        bool HasDocument();

        void LoadDocument(hstring const& filePath);
        void UnloadDocument();
        void RenderPage(uint32_t pageIndex);
        void ZoomToFit();
        void ZoomToWidth();
        void ZoomToHeight();
        void ZoomIn();
        void ZoomOut();
        void PanTo(double x, double y);

    protected:
        void OnCanvasPointerPressed(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);
        void OnCanvasPointerReleased(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);
        void OnCanvasPointerMoved(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);
        void OnCanvasPointerWheelChanged(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::Input::PointerRoutedEventArgs const& args);
        void OnCanvasDragOver(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::DragEventArgs const& args);
        void OnCanvasDrop(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::DragEventArgs const& args);

        void OnSearchBoxKeyDown(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::Input::KeyRoutedEventArgs const& args);
        void OnPrevResultClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnNextResultClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnCloseSearchClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);

        void OnPrevPageClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnNextPageClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnZoomOutClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnZoomInClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnZoomSliderChanged(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::Controls::Primitives::RangeBaseValueChangedEventArgs const& args);
        void OnZoomFitClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnZoomWidthClick(Windows::Foundation::IInspectable const& sender,
            Microsoft::UI::Xaml::RoutedEventArgs const& args);

    private:
        void UpdateCanvasSize();
        void UpdateZoomDisplay();
        void HandleSelection(double x, double y, bool addToSelection);

        double m_zoomLevel{ 100.0 };
        uint32_t m_currentPage{ 0 };
        uint32_t m_totalPages{ 0 };
        bool m_hasDocument{ false };
        bool m_isPanning{ false };
        bool m_isSelecting{ false };
        Microsoft::UI::Xaml::Point m_lastPanPoint{};
        Microsoft::UI::Xaml::Point m_selectionStart{};
        std::wstring m_documentPath;
        std::vector<Microsoft::UI::Xaml::Rect> m_selections;

        double m_pageWidth{ 612.0 };
        double m_pageHeight{ 792.0 };
        double m_margin{ 40.0 };
    };
}
