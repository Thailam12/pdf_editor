#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Services
{
    struct AIService
    {
        AIService();

        static AIService GetDefault();

        bool IsConnected() const;
        bool Connect(hstring const& serverUrl);
        void Disconnect();

        winrt::Windows::Foundation::IAsyncOperation<hstring> QueryAsync(hstring const& prompt);
        winrt::Windows::Foundation::IAsyncOperation<hstring> SummarizeDocumentAsync(hstring const& documentText);
        winrt::Windows::Foundation::IAsyncOperation<hstring> AnswerQuestionAsync(hstring const& question, hstring const& context);

        std::vector<hstring> IdentifySensitiveContent(hstring const& documentText);
        hstring TranslateText(hstring const& text, hstring const& targetLanguage);
        hstring ExtractKeyInformation(hstring const& documentText);

        winrt::Windows::Foundation::IAsyncAction StreamQuery(hstring const& prompt,
            std::function<void(hstring const&)> onToken);

        event_token StatusChanged(Windows::Foundation::EventHandler<bool> const& handler);
        void StatusChanged(event_token const& token) noexcept;

    private:
        std::wstring SendRequest(std::wstring const& endpoint, std::wstring const& body);
        std::wstring BuildPromptWithContext(hstring const& prompt, hstring const& context);

        std::wstring m_serverUrl{ L"http://localhost:8080" };
        bool m_connected{ false };
        std::wstring m_modelName{ L"pdfmind-100m" };
        std::mutex m_mutex;
        Windows::Foundation::EventHandler<bool> m_statusChangedHandler;

        std::vector<std::pair<std::wstring, std::wstring>> m_contextHistory;
    };
}
