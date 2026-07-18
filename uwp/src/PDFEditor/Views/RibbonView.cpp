#include "pch.h"
#include "Views/RibbonView.h"
#include "Views/RibbonView.g.cpp"
#include "Core/DocumentManager.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::PDFEditor::implementation
{
    RibbonView::RibbonView()
    {
        InitializeComponent();
        ShowTabContent(L"Home");
    }

    void RibbonView::SelectTab(hstring const& tabName)
    {
        ShowTabContent(std::wstring(tabName));
    }

    void RibbonView::OnTabClick(IInspectable const& sender, RoutedEventArgs const& args)
    {
        auto button = sender.as<Controls::Button>();
        if (!button) return;

        auto tag = button.Tag();
        if (tag)
        {
            auto tabName = winrt::unbox_value<hstring>(tag);
            ShowTabContent(std::wstring(tabName));

            auto children = TabHeaders().Children();
            for (uint32_t i = 0; i < children.Size(); ++i)
            {
                auto btn = children.GetAt(i).as<Controls::Button>();
                if (btn)
                {
                    btn.FontWeight(Microsoft::UI::Text::FontWeightHelper::FromRank(
                        btn == button ? 600 : 400));
                }
            }
        }
    }

    void RibbonView::ShowTabContent(std::wstring const& tabName)
    {
        auto hideAll = [this]()
        {
            if (HomeTabContent()) HomeTabContent().Visibility(Visibility::Collapsed);
            if (InsertTabContent()) InsertTabContent().Visibility(Visibility::Collapsed);
            if (AnnotateTabContent()) AnnotateTabContent().Visibility(Visibility::Collapsed);
            if (PageTabContent()) PageTabContent().Visibility(Visibility::Collapsed);
            if (ViewTabContent()) ViewTabContent().Visibility(Visibility::Collapsed);
            if (ToolsTabContent()) ToolsTabContent().Visibility(Visibility::Collapsed);
            if (HelpTabContent()) HelpTabContent().Visibility(Visibility::Collapsed);
            if (FileTabContent()) FileTabContent().Visibility(Visibility::Collapsed);
        };

        hideAll();

        if (tabName == L"Home" && HomeTabContent())
            HomeTabContent().Visibility(Visibility::Visible);
        else if (tabName == L"Insert" && InsertTabContent())
            InsertTabContent().Visibility(Visibility::Visible);
        else if (tabName == L"Annotate" && AnnotateTabContent())
            AnnotateTabContent().Visibility(Visibility::Visible);
        else if (tabName == L"Page" && PageTabContent())
            PageTabContent().Visibility(Visibility::Visible);
        else if (tabName == L"View" && ViewTabContent())
            ViewTabContent().Visibility(Visibility::Visible);
        else if (tabName == L"Tools" && ToolsTabContent())
            ToolsTabContent().Visibility(Visibility::Visible);
        else if (tabName == L"Help" && HelpTabContent())
            HelpTabContent().Visibility(Visibility::Visible);
        else if (tabName == L"File" && FileTabContent())
            FileTabContent().Visibility(Visibility::Visible);

        m_activeTab = tabName;
    }

    void RibbonView::OnAIClick(IInspectable const&, RoutedEventArgs const&)
    {
        auto app = Application::Current();
        if (app)
        {
            auto resources = app->Resources();
            if (resources)
            {
                auto event = resources.Lookup(winrt::box_value(L"AIToggleRequested"));
                if (event)
                {
                    auto func = event.try_as<Controls::Button>();
                }
            }
        }
    }

    void RibbonView::OnNewClick(IInspectable const&, RoutedEventArgs const&)
    {
        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager) docManager->NewDocument();
    }

    void RibbonView::OnOpenClick(IInspectable const&, RoutedEventArgs const&)
    {
        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager) docManager->PromptOpenDocument();
    }

    void RibbonView::OnSaveClick(IInspectable const&, RoutedEventArgs const&)
    {
        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager) docManager->SaveDocument();
    }

    void RibbonView::OnInsertImageClick(IInspectable const&, RoutedEventArgs const&)
    {
        OutputDebugStringW(L"[RibbonView] Insert Image\n");
    }

    void RibbonView::OnInsertPageClick(IInspectable const&, RoutedEventArgs const&)
    {
        OutputDebugStringW(L"[RibbonView] Insert Page\n");
    }
}
