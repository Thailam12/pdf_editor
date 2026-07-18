#include "pch.h"
#include "Views/EditorView.h"
#include "Views/EditorView.g.cpp"
#include "Core/DocumentManager.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;
using namespace Microsoft::UI::Xaml::Input;
using namespace Microsoft::UI::Xaml::Media;
using namespace Microsoft::UI::Xaml::Media::Imaging;
using namespace Windows::Foundation;

namespace winrt::PDFEditor::implementation
{
    EditorView::EditorView()
    {
        InitializeComponent();
    }

    double EditorView::ZoomLevel() { return m_zoomLevel; }
    void EditorView::ZoomLevel(double value)
    {
        m_zoomLevel = std::clamp(value, 10.0, 500.0);
        UpdateCanvasSize();
        UpdateZoomDisplay();
    }

    uint32_t EditorView::CurrentPage() { return m_currentPage; }
    void EditorView::CurrentPage(uint32_t value)
    {
        if (value != m_currentPage)
        {
            m_currentPage = value;
            RenderPage(m_currentPage);
        }
    }

    uint32_t EditorView::TotalPages() { return m_totalPages; }
    void EditorView::TotalPages(uint32_t value) { m_totalPages = value; }
    bool EditorView::HasDocument() { return m_hasDocument; }

    void EditorView::LoadDocument(hstring const& filePath)
    {
        m_documentPath = std::wstring(filePath);
        m_hasDocument = true;
        m_currentPage = 0;
        m_zoomLevel = 100.0;
        m_selections.clear();

        UpdateCanvasSize();
        RenderPage(0);
        UpdateZoomDisplay();
    }

    void EditorView::UnloadDocument()
    {
        m_hasDocument = false;
        m_documentPath.clear();
        m_totalPages = 0;
        m_currentPage = 0;
        m_selections.clear();

        if (PDFCanvas())
        {
            PDFCanvas().Children().Clear();
        }
    }

    void EditorView::RenderPage(uint32_t pageIndex)
    {
        if (!m_hasDocument) return;
        if (!PDFCanvas()) return;

        PDFCanvas().Children().Clear();

        auto scale = m_zoomLevel / 100.0;
        auto scaledWidth = m_pageWidth * scale;
        auto scaledHeight = m_pageHeight * scale;

        PDFCanvas().Width(scaledWidth + m_margin * 2);
        PDFCanvas().Height(scaledHeight + m_margin * 2);

        auto border = Microsoft::UI::Xaml::Controls::Border();
        border.Width(scaledWidth);
        border.Height(scaledHeight);
        border.Background(Brushes::White());
        border.BorderBrush(Brushes::Gray());
        border.BorderThickness(ThicknessHelper::FromLengths(0.5, 0.5, 0.5, 0.5));

        auto shadow = Microsoft::UI::Xaml::Media::Media3D::PlaneProjection();
        Microsoft::UI::Xaml::Controls::Canvas::SetLeft(border, m_margin);
        Microsoft::UI::Xaml::Controls::Canvas::SetTop(border, m_margin);

        auto pageLabel = TextBlock();
        pageLabel.Text(L"Page " + winrt::to_hstring(pageIndex + 1));
        pageLabel.HorizontalAlignment(HorizontalAlignment::Center);
        pageLabel.Margin(ThicknessHelper::FromLengths(0, 8, 0, 0));
        pageLabel.FontSize(11);
        pageLabel.Foreground(Brushes::Gray());

        auto container = Grid();
        container.Children().Append(border);
        container.Width(scaledWidth);
        container.Height(scaledHeight);

        PDFCanvas().Children().Append(container);
    }

    void EditorView::ZoomToFit()
    {
        auto scroller = CanvasScroller();
        if (!scroller) return;

        auto viewportWidth = scroller.ActualWidth() - 80;
        auto viewportHeight = scroller.ActualHeight() - 80;

        auto scaleX = viewportWidth / m_pageWidth;
        auto scaleY = viewportHeight / m_pageHeight;
        m_zoomLevel = std::min(scaleX, scaleY) * 100.0;
        m_zoomLevel = std::clamp(m_zoomLevel, 10.0, 500.0);

        UpdateCanvasSize();
        UpdateZoomDisplay();
        RenderPage(m_currentPage);
    }

    void EditorView::ZoomToWidth()
    {
        auto scroller = CanvasScroller();
        if (!scroller) return;

        auto viewportWidth = scroller.ActualWidth() - 80;
        m_zoomLevel = (viewportWidth / m_pageWidth) * 100.0;
        m_zoomLevel = std::clamp(m_zoomLevel, 10.0, 500.0);

        UpdateCanvasSize();
        UpdateZoomDisplay();
        RenderPage(m_currentPage);
    }

    void EditorView::ZoomToHeight()
    {
        auto scroller = CanvasScroller();
        if (!scroller) return;

        auto viewportHeight = scroller.ActualHeight() - 80;
        m_zoomLevel = (viewportHeight / m_pageHeight) * 100.0;
        m_zoomLevel = std::clamp(m_zoomLevel, 10.0, 500.0);

        UpdateCanvasSize();
        UpdateZoomDisplay();
        RenderPage(m_currentPage);
    }

    void EditorView::ZoomIn()
    {
        m_zoomLevel = std::min(m_zoomLevel + 25.0, 500.0);
        UpdateCanvasSize();
        UpdateZoomDisplay();
        RenderPage(m_currentPage);
    }

    void EditorView::ZoomOut()
    {
        m_zoomLevel = std::max(m_zoomLevel - 25.0, 10.0);
        UpdateCanvasSize();
        UpdateZoomDisplay();
        RenderPage(m_currentPage);
    }

    void EditorView::PanTo(double x, double y)
    {
        auto scroller = CanvasScroller();
        if (scroller)
        {
            scroller.ScrollToHorizontalOffset(x);
            scroller.ScrollToVerticalOffset(y);
        }
    }

    void EditorView::UpdateCanvasSize()
    {
        auto scale = m_zoomLevel / 100.0;
        if (PDFCanvas())
        {
            PDFCanvas().Width(m_pageWidth * scale + m_margin * 2);
            PDFCanvas().Height(m_pageHeight * scale + m_margin * 2);
        }
    }

    void EditorView::UpdateZoomDisplay()
    {
        if (ZoomSlider())
            ZoomSlider().Value(m_zoomLevel);
        if (ZoomLabel())
            ZoomLabel().Text(winrt::to_hstring(static_cast<int>(m_zoomLevel)) + L"%");
    }

    void EditorView::HandleSelection(double x, double y, bool addToSelection)
    {
        if (!addToSelection)
        {
            m_selections.clear();
        }

        double selSize = 100.0;
        m_selections.push_back(
            Microsoft::UI::Xaml::Rect(
                static_cast<float>(x - selSize / 2),
                static_cast<float>(y - selSize / 2),
                static_cast<float>(selSize),
                static_cast<float>(selSize)));

        if (SelectionOverlay())
        {
            SelectionOverlay().Children().Clear();
            for (auto const& sel : m_selections)
            {
                auto rect = Microsoft::UI::Xaml::Shapes::Rectangle();
                rect.Width(sel.Width);
                rect.Height(sel.Height);
                rect.Stroke(Brushes::DodgerBlue());
                rect.StrokeThickness(2);
                rect.StrokeDashArray(SingleCollection({ 4.0, 2.0 }));
                rect.Fill(SolidColorBrush(winrt::Windows::UI::ColorHelper::FromArgb(30, 30, 144, 255)));

                Microsoft::UI::Xaml::Controls::Canvas::SetLeft(rect, sel.X);
                Microsoft::UI::Xaml::Controls::Canvas::SetTop(rect, sel.Y);
                SelectionOverlay().Children().Append(rect);
            }
        }
    }

    void EditorView::OnCanvasPointerPressed(IInspectable const&, PointerRoutedEventArgs const& args)
    {
        auto props = args.GetCurrentPoint(nullptr).Properties();
        if (props.IsLeftButtonPressed())
        {
            auto point = args.GetCurrentPoint(nullptr);
            auto position = point.Position();

            if (props.IsXButton1Pressed() || Microsoft::UI::Input::InputKeyboardSource::GetKeyStateForCurrentThread(Windows::System::VirtualKey::Space) == Microsoft::UI::Input::VirtualKeyStates::Down)
            {
                m_isPanning = true;
                m_lastPanPoint = position;
                args.Handled(true);
            }
            else
            {
                auto ctrl = Microsoft::UI::Input::InputKeyboardSource::GetKeyStateForCurrentThread(Windows::System::VirtualKeyModifiers::Control);
                bool addToSelection = (ctrl & Microsoft::UI::Input::VirtualKeyStates::Down) == Microsoft::UI::Input::VirtualKeyStates::Down;
                HandleSelection(position.X, position.Y, addToSelection);
            }
        }
    }

    void EditorView::OnCanvasPointerReleased(IInspectable const&, PointerRoutedEventArgs const&)
    {
        m_isPanning = false;
        m_isSelecting = false;
    }

    void EditorView::OnCanvasPointerMoved(IInspectable const&, PointerRoutedEventArgs const& args)
    {
        if (m_isPanning)
        {
            auto point = args.GetCurrentPoint(nullptr);
            auto position = point.Position();

            auto scroller = CanvasScroller();
            if (scroller)
            {
                auto dx = position.X - m_lastPanPoint.X;
                auto dy = position.Y - m_lastPanPoint.Y;
                scroller.ScrollToHorizontalOffset(scroller.HorizontalOffset() - dx);
                scroller.ScrollToVerticalOffset(scroller.VerticalOffset() - dy);
            }

            m_lastPanPoint = position;
            args.Handled(true);
        }
    }

    void EditorView::OnCanvasPointerWheelChanged(IInspectable const&, PointerRoutedEventArgs const& args)
    {
        auto ctrl = Microsoft::UI::Input::InputKeyboardSource::GetKeyStateForCurrentThread(Windows::System::VirtualKeyModifiers::Control);
        bool isCtrl = (ctrl & Microsoft::UI::Input::VirtualKeyStates::Down) == Microsoft::UI::Input::VirtualKeyStates::Down;

        if (isCtrl)
        {
            auto delta = args.GetCurrentPoint(nullptr).Properties().MouseWheelDelta();
            if (delta > 0)
            {
                m_zoomLevel = std::min(m_zoomLevel + 10.0, 500.0);
            }
            else
            {
                m_zoomLevel = std::max(m_zoomLevel - 10.0, 10.0);
            }

            UpdateCanvasSize();
            UpdateZoomDisplay();
            RenderPage(m_currentPage);
            args.Handled(true);
        }
    }

    void EditorView::OnCanvasDragOver(IInspectable const&, DragEventArgs const& args)
    {
        auto dataView = args.DataView();
        if (dataView.Contains(Windows::ApplicationModel::DataTransfer::StandardDataFormats::StorageItems()))
        {
            args.DragUIOverride().Caption(L"Open PDF");
            args.DragUIOverride().IsCaptionVisible(true);
            args.AcceptedOperation(Windows::ApplicationModel::DataTransfer::DataPackageOperation::Copy);
        }
    }

    void EditorView::OnCanvasDrop(IInspectable const&, DragEventArgs const& args)
    {
        auto dataView = args.DataView();
        if (dataView.Contains(Windows::ApplicationModel::DataTransfer::StandardDataFormats::StorageItems()))
        {
            auto asyncOp = dataView.GetStorageItemsAsync();
            asyncOp.Completed([this](auto const& op, auto const&)
            {
                auto items = op.GetResults();
                for (auto const& item : items)
                {
                    auto storageFile = item.as<Windows::Storage::StorageFile>();
                    if (storageFile)
                    {
                        auto path = storageFile.Path();
                        if (path.ends_with(L".pdf") || path.ends_with(L".PDF"))
                        {
                            RunOnUIThread([this, path]()
                            {
                                LoadDocument(path);
                            });
                        }
                    }
                }
            });
        }
    }

    void EditorView::OnSearchBoxKeyDown(IInspectable const& sender, KeyRoutedEventArgs const& args)
    {
        if (args.Key() == Windows::System::VirtualKey::Enter)
        {
            auto textBox = sender.as<TextBox>();
            if (textBox)
            {
                auto query = textBox.Text();
                if (!query.empty())
                {
                    auto count = winrt::to_hstring(0);
                    if (SearchResultCount())
                        SearchResultCount().Text(count + L" results");
                }
            }
        }
        else if (args.Key() == Windows::System::VirtualKey::Escape)
        {
            if (SearchBar())
                SearchBar().Visibility(Visibility::Collapsed);
        }
    }

    void EditorView::OnPrevResultClick(IInspectable const&, RoutedEventArgs const&) {}
    void EditorView::OnNextResultClick(IInspectable const&, RoutedEventArgs const&) {}

    void EditorView::OnCloseSearchClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (SearchBar())
            SearchBar().Visibility(Visibility::Collapsed);
    }

    void EditorView::OnPrevPageClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_currentPage > 0)
        {
            m_currentPage--;
            RenderPage(m_currentPage);
        }
    }

    void EditorView::OnNextPageClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_currentPage + 1 < m_totalPages)
        {
            m_currentPage++;
            RenderPage(m_currentPage);
        }
    }

    void EditorView::OnZoomOutClick(IInspectable const&, RoutedEventArgs const&) { ZoomOut(); }
    void EditorView::OnZoomInClick(IInspectable const&, RoutedEventArgs const&) { ZoomIn(); }

    void EditorView::OnZoomSliderChanged(IInspectable const&,
        Controls::Primitives::RangeBaseValueChangedEventArgs const& args)
    {
        if (m_zoomLevel != args.NewValue())
        {
            m_zoomLevel = args.NewValue();
            UpdateCanvasSize();
            RenderPage(m_currentPage);
            UpdateZoomDisplay();
        }
    }

    void EditorView::OnZoomFitClick(IInspectable const&, RoutedEventArgs const&) { ZoomToFit(); }
    void EditorView::OnZoomWidthClick(IInspectable const&, RoutedEventArgs const&) { ZoomToWidth(); }
}
