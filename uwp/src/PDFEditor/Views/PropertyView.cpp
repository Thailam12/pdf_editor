#include "pch.h"
#include "Views/PropertyView.h"
#include "Views/PropertyView.g.cpp"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::PDFEditor::implementation
{
    PropertyView::PropertyView()
    {
        InitializeComponent();
    }

    void PropertyView::SetSelection(IInspectable const&)
    {
        m_hasSelection = true;
        if (NoSelectionPanel()) NoSelectionPanel().Visibility(Visibility::Collapsed);
        if (SelectionPropsPanel()) SelectionPropsPanel().Visibility(Visibility::Visible);
    }

    void PropertyView::ClearSelection()
    {
        m_hasSelection = false;
        if (NoSelectionPanel()) NoSelectionPanel().Visibility(Visibility::Visible);
        if (SelectionPropsPanel()) SelectionPropsPanel().Visibility(Visibility::Collapsed);
    }

    void PropertyView::OnCollapseClick(IInspectable const&, RoutedEventArgs const&)
    {
        this->Visibility(Visibility::Collapsed);
    }
}
