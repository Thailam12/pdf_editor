#include "pch.h"
#include "Views/SearchView.h"
#include "Views/SearchView.g.cpp"
#include "Core/DocumentManager.h"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::PDFEditor::implementation
{
    SearchView::SearchView()
    {
        InitializeComponent();
    }

    void SearchView::Search(hstring const& query)
    {
        if (query.empty()) return;

        m_results.clear();
        m_currentResultIndex = 0;

        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager && docManager->CurrentDocument())
        {
            auto pageCount = docManager->CurrentDocument()->PageCount();
            bool matchCase = MatchCaseCheck() && MatchCaseCheck()->IsChecked().Value();
            bool wholeWord = WholeWordCheck() && WholeWordCheck()->IsChecked().Value();

            for (int page = 0; page < pageCount; ++page)
            {
                m_results.push_back({ page, 0, L"Match on page " + std::to_wstring(page + 1) });
            }
        }

        if (ResultsList())
        {
            auto items = winrt::single_threaded_vector<hstring>();
            for (auto const& [page, pos, text] : m_results)
            {
                items.Append(text);
            }
            ResultsList().ItemsSource(items);
        }

        if (ResultCountText())
        {
            auto count = winrt::to_hstring(static_cast<int>(m_results.size()));
            ResultCountText().Text(count + L" results found");
        }
    }

    void SearchView::ReplaceAll(hstring const& find, hstring const& replace)
    {
        if (find.empty()) return;

        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager)
        {
            auto cmdManager = Core::CommandManager::GetDefault();
            if (cmdManager)
            {
                cmdManager->BeginMacro(L"ReplaceAll");
                for (auto const& [page, pos, text] : m_results)
                {
                    cmdManager->ExecuteCommand(L"ReplaceText",
                        L"page=" + std::to_wstring(page) +
                        L";find=" + std::wstring(find) +
                        L";replace=" + std::wstring(replace));
                }
                cmdManager->EndMacro();
            }
        }

        Search(find);
    }

    void SearchView::ReplaceSelected(hstring const& find, hstring const& replace)
    {
        if (find.empty() || m_results.empty()) return;

        if (m_currentResultIndex >= 0 && m_currentResultIndex < static_cast<int>(m_results.size()))
        {
            auto [page, pos, text] = m_results[m_currentResultIndex];
            auto docManager = Core::DocumentManager::GetDefault();
            if (docManager)
            {
                auto cmdManager = Core::CommandManager::GetDefault();
                if (cmdManager)
                {
                    cmdManager->ExecuteCommand(L"ReplaceText",
                        L"page=" + std::to_wstring(page) +
                        L";find=" + std::wstring(find) +
                        L";replace=" + std::wstring(replace));
                }
            }
        }
    }

    void SearchView::OnFindNextClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (m_results.empty()) return;

        m_currentResultIndex = (m_currentResultIndex + 1) % static_cast<int>(m_results.size());

        if (ResultsList())
        {
            ResultsList().SelectedIndex(m_currentResultIndex);
            ResultsList().ScrollIntoView(
                ResultsList().SelectedItem());
        }

        auto [page, pos, text] = m_results[m_currentResultIndex];
        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager && docManager->CurrentDocument())
        {
            docManager->CurrentDocument().CurrentPage(page);
        }
    }

    void SearchView::OnFindAllClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (SearchInput())
        {
            Search(SearchInput().Text());
        }
    }

    void SearchView::OnReplaceClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (SearchInput() && ReplaceInput())
        {
            ReplaceSelected(SearchInput().Text(), ReplaceInput().Text());
            OnFindNextClick(nullptr, RoutedEventArgs());
        }
    }

    void SearchView::OnReplaceAllClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (SearchInput() && ReplaceInput())
        {
            ReplaceAll(SearchInput().Text(), ReplaceInput().Text());
        }
    }

    void SearchView::OnResultItemClick(IInspectable const&, Controls::ItemClickEventArgs const& args)
    {
        auto item = args.ClickedItem().as<hstring>();
        if (m_currentResultIndex >= 0 && m_currentResultIndex < static_cast<int>(m_results.size()))
        {
            auto [page, pos, text] = m_results[m_currentResultIndex];
            auto docManager = Core::DocumentManager::GetDefault();
            if (docManager && docManager->CurrentDocument())
            {
                docManager->CurrentDocument().CurrentPage(page);
            }
        }
    }
}
