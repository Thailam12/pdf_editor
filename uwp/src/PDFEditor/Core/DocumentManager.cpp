#include "pch.h"
#include "Core/DocumentManager.h"
#include "Core/DocumentManager.g.cpp"
#include "Core/CommandManager.h"
#include "Core/SettingsManager.h"

using namespace winrt;
using namespace Windows::Foundation;
using namespace Windows::Foundation::Collections;

namespace winrt::PDFEditor::implementation
{
    static std::shared_ptr<DocumentManager> s_instance{ nullptr };
    static std::mutex s_instanceMutex;

    DocumentManager::DocumentManager()
    {
        LoadRecentFiles();
        m_commandManager = winrt::make<CommandManager>();
    }

    Core::DocumentManager DocumentManager::GetDefault()
    {
        std::lock_guard lock(s_instanceMutex);
        if (!s_instance)
        {
            s_instance = std::make_shared<DocumentManager>();
        }
        auto boxed = winrt::make<DocumentManager>();
        return boxed.as<Core::DocumentManager>();
    }

    Core::DocumentInfo DocumentManager::CurrentDocument()
    {
        std::lock_guard lock(m_mutex);
        if (m_activeDocIndex >= 0 && m_activeDocIndex < static_cast<int>(m_documents.size()))
        {
            return m_documents[m_activeDocIndex];
        }
        return nullptr;
    }

    Core::DocumentInfo DocumentManager::OpenDocument(hstring const& filePath)
    {
        std::lock_guard lock(m_mutex);

        for (auto const& doc : m_documents)
        {
            if (doc && doc.FilePath() == filePath)
            {
                m_activeDocIndex = static_cast<int32_t>(
                    std::distance(m_documents.begin(),
                        std::find(m_documents.begin(), m_documents.end(), doc)));
                NotifyDocumentOpened(doc);
                return doc;
            }
        }

        auto docInfo = winrt::make<DocumentInfo>();
        docInfo.FilePath(filePath);

        auto path = std::wstring(filePath);
        docInfo.DisplayName(std::filesystem::path(path).filename().wstring());

        if (std::filesystem::exists(path))
        {
            auto lastWrite = std::filesystem::last_write_time(path);
            auto fileTime = FILETIME{};
            auto duration = lastWrite.time_since_epoch().count();
            auto ticks = duration * 100;
            auto ft =ULARGE_INTEGER{};
            ft.QuadPart = ticks;
            fileTime.dwLowDateTime = ft.LowPart;
            fileTime.dwHighDateTime = ft.HighPart;
        }

        docInfo.PageCount(1);
        docInfo.CurrentPage(0);
        docInfo.IsModified(false);

        m_documents.push_back(docInfo);
        m_activeDocIndex = static_cast<int32_t>(m_documents.size() - 1);

        AddRecentFile(filePath);
        NotifyDocumentOpened(docInfo);

        OutputDebugStringW(L"[DocumentManager] Opened: ");
        OutputDebugStringW(filePath.c_str());
        OutputDebugStringW(L"\n");

        return docInfo;
    }

    void DocumentManager::PromptOpenDocument()
    {
        auto asyncOp = [this]() -> winrt::IAsyncAction
        {
            auto picker = Windows::Storage::Pickers::FileOpenPicker();
            picker.SuggestedStartLocation(Windows::Storage::Pickers::PickerLocationId::Desktop);

            auto initializeWithWindow =
                picker.as<::IInitializeWithWindow>();
            auto appWindow = Microsoft::UI::Xaml::Application::Current()
                .as<winrt::PDFEditor::implementation::Application>();

            picker.FileTypeFilter().Append(L".pdf");
            picker.FileTypeFilter().Append(L".xps");
            picker.FileTypeFilter().Append(L".cbz");

            auto file = co_await picker.PickSingleFileAsync();
            if (file)
            {
                OpenDocument(file.Path());
            }
        };
        asyncOp();
    }

    void DocumentManager::SaveDocument()
    {
        std::lock_guard lock(m_mutex);
        if (m_activeDocIndex < 0 || m_activeDocIndex >= static_cast<int>(m_documents.size()))
            return;

        auto doc = m_documents[m_activeDocIndex];
        if (!doc) return;

        if (doc.FilePath().empty())
        {
            SaveDocumentAs();
            return;
        }

        doc.IsModified(false);

        if (m_documentModifiedHandlers)
        {
            m_documentModifiedHandlers(nullptr, false);
        }
    }

    void DocumentManager::SaveDocumentAs()
    {
        auto asyncOp = [this]() -> winrt::IAsyncAction
        {
            auto picker = Windows::Storage::Pickers::FileSavePicker();
            picker.SuggestedStartLocation(Windows::Storage::Pickers::PickerLocationId::Desktop);
            picker.SuggestedFileName(L"Untitled.pdf");
            picker.FileTypeChoices().Append(L"PDF Document", winrt::single_vector<hstring>({L".pdf"}));
            picker.FileTypeChoices().Append(L"All Files", winrt::single_vector<hstring>({L".*"}));

            auto file = co_await picker.PickSaveFileAsync();
            if (file)
            {
                std::lock_guard lock(m_mutex);
                if (m_activeDocIndex >= 0 && m_activeDocIndex < static_cast<int>(m_documents.size()))
                {
                    auto doc = m_documents[m_activeDocIndex];
                    if (doc)
                    {
                        doc.FilePath(file.Path());
                        doc.DisplayName(std::filesystem::path(file.Path()).filename().wstring());
                        doc.IsModified(false);
                        AddRecentFile(file.Path());
                    }
                }
            }
        };
        asyncOp();
    }

    void DocumentManager::CloseDocument(int32_t index)
    {
        std::lock_guard lock(m_mutex);
        if (index < 0 || index >= static_cast<int>(m_documents.size()))
            return;

        auto doc = m_documents[index];
        if (doc)
        {
            NotifyDocumentClosed(doc);
        }

        m_documents.erase(m_documents.begin() + index);

        if (m_activeDocIndex >= static_cast<int>(m_documents.size()))
        {
            m_activeDocIndex = static_cast<int>(m_documents.size()) - 1;
        }
    }

    void DocumentManager::NewDocument()
    {
        auto docInfo = winrt::make<DocumentInfo>();
        docInfo.DisplayName(L"Untitled");
        docInfo.PageCount(0);
        docInfo.CurrentPage(0);
        docInfo.IsModified(false);

        std::lock_guard lock(m_mutex);
        m_documents.push_back(docInfo);
        m_activeDocIndex = static_cast<int32_t>(m_documents.size() - 1);

        NotifyDocumentOpened(docInfo);
    }

    bool DocumentManager::Undo()
    {
        if (m_commandManager)
        {
            return m_commandManager->Undo();
        }
        return false;
    }

    bool DocumentManager::Redo()
    {
        if (m_commandManager)
        {
            return m_commandManager->Redo();
        }
        return false;
    }

    IVector<Core::DocumentTab> DocumentManager::OpenTabs()
    {
        auto tabs = winrt::single_threaded_vector<Core::DocumentTab>();
        std::lock_guard lock(m_mutex);

        for (int32_t i = 0; i < static_cast<int32_t>(m_documents.size()); ++i)
        {
            auto tab = winrt::make<DocumentTab>();
            tab.Index(i);
            tab.Info(m_documents[i]);
            tab.IsActive(i == m_activeDocIndex);
            tabs.Append(tab);
        }

        return tabs;
    }

    IVector<hstring> DocumentManager::RecentFiles()
    {
        std::lock_guard lock(m_mutex);
        auto vec = winrt::single_threaded_vector<hstring>();
        for (auto const& file : m_recentFiles)
        {
            vec.Append(file);
        }
        return vec;
    }

    void DocumentManager::AddRecentFile(hstring const& filePath)
    {
        std::lock_guard lock(m_mutex);

        auto it = std::find(m_recentFiles.begin(), m_recentFiles.end(), filePath);
        if (it != m_recentFiles.end())
        {
            m_recentFiles.erase(it);
        }

        m_recentFiles.insert(m_recentFiles.begin(), filePath);

        constexpr size_t maxRecentFiles = 25;
        if (m_recentFiles.size() > maxRecentFiles)
        {
            m_recentFiles.resize(maxRecentFiles);
        }

        SaveRecentFiles();
    }

    void DocumentManager::ClearRecentFiles()
    {
        std::lock_guard lock(m_mutex);
        m_recentFiles.clear();
        SaveRecentFiles();
    }

    void DocumentManager::LoadRecentFiles()
    {
        auto settings = SettingsManager::GetDefault();
        if (settings)
        {
            m_recentFiles.clear();
            auto recentCountStr = settings->GetSetting(L"RecentFileCount");
            int count = 0;
            try { count = std::stoi(std::wstring(recentCountStr)); }
            catch (...) { count = 0; }

            for (int i = 0; i < count && i < 25; ++i)
            {
                auto path = settings->GetSetting(L"RecentFile_" + std::to_wstring(i));
                if (!path.empty())
                {
                    m_recentFiles.push_back(path);
                }
            }
        }
    }

    void DocumentManager::SaveRecentFiles()
    {
        auto settings = SettingsManager::GetDefault();
        if (settings)
        {
            settings->SetSetting(L"RecentFileCount", std::to_wstring(m_recentFiles.size()));
            for (size_t i = 0; i < m_recentFiles.size(); ++i)
            {
                settings->SetSetting(L"RecentFile_" + std::to_wstring(i), m_recentFiles[i]);
            }
        }
    }

    event_token DocumentManager::DocumentOpened(EventHandler<Core::DocumentInfo> const& handler)
    {
        return m_documentOpenedHandler.add(handler);
    }

    void DocumentManager::DocumentOpened(event_token const& token) noexcept
    {
        m_documentOpenedHandler.remove(token);
    }

    event_token DocumentManager::DocumentClosed(EventHandler<Core::DocumentInfo> const& handler)
    {
        return m_documentClosedHandler.add(handler);
    }

    void DocumentManager::DocumentClosed(event_token const& token) noexcept
    {
        m_documentClosedHandler.remove(token);
    }

    event_token DocumentManager::DocumentModifiedChanged(EventHandler<bool> const& handler)
    {
        return m_documentModifiedHandler.add(handler);
    }

    void DocumentManager::DocumentModifiedChanged(event_token const& token) noexcept
    {
        m_documentModifiedHandler.remove(token);
    }

    void DocumentManager::NotifyDocumentOpened(Core::DocumentInfo const& info)
    {
        if (m_documentOpenedHandler)
        {
            m_documentOpenedHandler(nullptr, info);
        }
    }

    void DocumentManager::NotifyDocumentClosed(Core::DocumentInfo const& info)
    {
        if (m_documentClosedHandler)
        {
            m_documentClosedHandler(nullptr, info);
        }
    }
}
