#pragma once

#include "Core/DocumentManager.g.h"

namespace winrt::PDFEditor::implementation
{
    struct DocumentInfo : DocumentInfoT<DocumentInfo>
    {
        DocumentInfo() = default;

        hstring FilePath() const { return m_filePath; }
        void FilePath(hstring const& value) { m_filePath = value; }

        hstring DisplayName() const { return m_displayName; }
        void DisplayName(hstring const& value) { m_displayName = value; }

        bool IsModified() const { return m_isModified; }
        void IsModified(bool value) { m_isModified = value; }

        int32_t PageCount() const { return m_pageCount; }
        void PageCount(int32_t value) { m_pageCount = value; }

        int32_t CurrentPage() const { return m_currentPage; }
        void CurrentPage(int32_t value) { m_currentPage = value; }

        Windows::Foundation::DateTime LastModified() const { return m_lastModified; }
        void LastModified(Windows::Foundation::DateTime const& value) { m_lastModified = value; }

    private:
        hstring m_filePath;
        hstring m_displayName;
        bool m_isModified{ false };
        int32_t m_pageCount{ 0 };
        int32_t m_currentPage{ 0 };
        Windows::Foundation::DateTime m_lastModified{};
    };

    struct DocumentTab : DocumentTabT<DocumentTab>
    {
        DocumentTab() = default;

        int32_t Index() const { return m_index; }
        void Index(int32_t value) { m_index = value; }

        Core::DocumentInfo Info() const { return m_info; }
        void Info(Core::DocumentInfo const& value) { m_info = value; }

        bool IsActive() const { return m_isActive; }
        void IsActive(bool value) { m_isActive = value; }

    private:
        int32_t m_index{ 0 };
        Core::DocumentInfo m_info{ nullptr };
        bool m_isActive{ false };
    };

    struct DocumentManager : DocumentManagerT<DocumentManager>
    {
        DocumentManager();

        static Core::DocumentManager GetDefault();
        Core::DocumentInfo CurrentDocument();

        Core::DocumentInfo OpenDocument(hstring const& filePath);
        void PromptOpenDocument();
        void SaveDocument();
        void SaveDocumentAs();
        void CloseDocument(int32_t index);
        void NewDocument();

        bool Undo();
        bool Redo();

        Windows::Foundation::Collections::IVector<Core::DocumentTab> OpenTabs();
        Windows::Foundation::Collections::IVector<hstring> RecentFiles();

        void AddRecentFile(hstring const& filePath);
        void ClearRecentFiles();

        event_token DocumentOpened(Windows::Foundation::EventHandler<Core::DocumentInfo> const& handler);
        void DocumentOpened(event_token const& token) noexcept;
        event_token DocumentClosed(Windows::Foundation::EventHandler<Core::DocumentInfo> const& handler);
        void DocumentClosed(event_token const& token) noexcept;
        event_token DocumentModifiedChanged(Windows::Foundation::EventHandler<bool> const& handler);
        void DocumentModifiedChanged(event_token const& token) noexcept;

    private:
        void LoadRecentFiles();
        void SaveRecentFiles();
        void NotifyDocumentOpened(Core::DocumentInfo const& info);
        void NotifyDocumentClosed(Core::DocumentInfo const& info);

        std::vector<Core::DocumentInfo> m_documents;
        int32_t m_activeDocIndex{ -1 };
        std::vector<hstring> m_recentFiles;
        Core::CommandManager m_commandManager{ nullptr };

        std::mutex m_mutex;
        event_token m_docOpenedToken{};
        event_token m_docClosedToken{};
        event_token m_docModifiedToken{};

        Windows::Foundation::EventHandler<Core::DocumentInfo> m_documentOpenedHandlers;
        Windows::Foundation::EventHandler<Core::DocumentInfo> m_documentClosedHandlers;
        Windows::Foundation::EventHandler<bool> m_documentModifiedHandlers;
    };
}
