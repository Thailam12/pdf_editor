#pragma once

#include "Views/PropertyView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct PropertyView : PropertyViewT<PropertyView>
    {
        PropertyView();

        void SetSelection(Windows::Foundation::IInspectable const& element);
        void ClearSelection();

    protected:
        void OnCollapseClick(Windows::Foundation::IInspectable const& sender,
                             Microsoft::UI::Xaml::RoutedEventArgs const& args);

    private:
        bool m_hasSelection{ false };
    };
}
