#pragma once

#include "Views/LayersView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct LayersView : LayersViewT<LayersView>
    {
        LayersView();
        void RefreshLayers();
    };
}
