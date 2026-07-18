#include "pch.h"
#include "Services/AIService.h"

using namespace winrt;

namespace winrt::PDFEditor::Services
{
    static std::shared_ptr<AIService> s_instance{ nullptr };
    static std::mutex s_instanceMutex;

    AIService::AIService()
    {
    }

    AIService AIService::GetDefault()
    {
        std::lock_guard lock(s_instanceMutex);
        if (!s_instance)
        {
            s_instance = std::make_shared<AIService>();
        }
        return *s_instance;
    }

    bool AIService::IsConnected() const
    {
        return m_connected;
    }

    bool AIService::Connect(hstring const& serverUrl)
    {
        std::lock_guard lock(m_mutex);
        m_serverUrl = std::wstring(serverUrl);

        auto result = SendRequest(L"/health", L"");
        m_connected = !result.empty();

        if (m_statusChangedHandler)
        {
            m_statusChangedHandler(nullptr, m_connected);
        }

        OutputDebugStringW(L"[AIService] Connected: ");
        OutputDebugStringW(m_connected ? L"true" : L"false");
        OutputDebugStringW(L"\n");

        return m_connected;
    }

    void AIService::Disconnect()
    {
        std::lock_guard lock(m_mutex);
        m_connected = false;
        m_contextHistory.clear();

        if (m_statusChangedHandler)
        {
            m_statusChangedHandler(nullptr, false);
        }
    }

    winrt::Windows::Foundation::IAsyncOperation<hstring> AIService::QueryAsync(hstring const& prompt)
    {
        co_await winrt::resume_background();

        if (!m_connected)
        {
            co_return L"AI service is not connected. Please ensure the llama.cpp server is running.";
        }

        auto body = L"{\"prompt\": \"" + std::wstring(prompt) + L"\", \"model\": \"" + m_modelName + L"\"}";
        auto result = SendRequest(L"/completion", body);

        if (result.empty())
        {
            co_return L"Failed to get response from AI service.";
        }

        co_return hstring(result);
    }

    winrt::Windows::Foundation::IAsyncOperation<hstring> AIService::SummarizeDocumentAsync(hstring const& documentText)
    {
        auto prompt = L"Please provide a comprehensive summary of the following document. "
                      L"Include key points, main topics, conclusions, and any important details:\n\n" +
                      std::wstring(documentText);

        co_return co_await QueryAsync(hstring(prompt));
    }

    winrt::Windows::Foundation::IAsyncOperation<hstring> AIService::AnswerQuestionAsync(hstring const& question, hstring const& context)
    {
        auto prompt = L"Based on the following document context, answer this question:\n" +
                      std::wstring(question) +
                      L"\n\nDocument context:\n" +
                      std::wstring(context);

        co_return co_await QueryAsync(hstring(prompt));
    }

    std::vector<hstring> AIService::IdentifySensitiveContent(hstring const& documentText)
    {
        std::vector<hstring> results;

        auto patterns = std::vector<std::pair<std::wstring, std::wstring>>{
            {L"\\b\\d{3}-\\d{2}-\\d{4}\\b", L"SSN"},
            {L"\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b", L"Credit Card"},
            {L"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b", L"Email"},
            {L"\\b\\(\\d{3}\\)\\s?\\d{3}-\\d{4}\\b", L"Phone Number"},
            {L"\\b\\d{1,5}\\s\\w+\\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)\\b", L"Street Address"},
        };

        auto text = std::wstring(documentText);
        for (auto const& [pattern, type] : patterns)
        {
            size_t pos = 0;
            while ((pos = text.find(type, pos)) != std::wstring::npos)
            {
                results.push_back(type + L" found at position " + std::to_wstring(pos));
                pos += type.length();
            }
        }

        return results;
    }

    hstring AIService::TranslateText(hstring const& text, hstring const& targetLanguage)
    {
        auto prompt = L"Translate the following text to " + std::wstring(targetLanguage) +
                      L". Provide only the translation:\n\n" + std::wstring(text);

        auto body = L"{\"prompt\": \"" + prompt + L"\", \"model\": \"" + m_modelName + L"\"}";
        auto result = SendRequest(L"/completion", body);
        return hstring(result);
    }

    hstring AIService::ExtractKeyInformation(hstring const& documentText)
    {
        auto prompt = L"Extract key information from this document. Include: "
                      L"dates, names, organizations, monetary amounts, "
                      L"key decisions, and action items:\n\n" + std::wstring(documentText);

        auto body = L"{\"prompt\": \"" + prompt + L"\", \"model\": \"" + m_modelName + L"\"}";
        auto result = SendRequest(L"/completion", body);
        return hstring(result);
    }

    winrt::Windows::Foundation::IAsyncAction AIService::StreamQuery(hstring const& prompt,
        std::function<void(hstring const&)> onToken)
    {
        co_await winrt::resume_background();

        if (!m_connected)
        {
            if (onToken) onToken(L"AI service is not connected.");
            co_return;
        }

        auto body = L"{\"prompt\": \"" + std::wstring(prompt) + L"\", \"model\": \"" + m_modelName + L"\", \"stream\": true}";
        auto result = SendRequest(L"/completion", body);

        std::wistringstream stream(result);
        std::wstring token;
        while (std::getline(stream, token, L'\n'))
        {
            if (!token.empty() && onToken)
            {
                onToken(hstring(token));
            }
        }
    }

    std::wstring AIService::SendRequest(std::wstring const& endpoint, std::wstring const& body)
    {
        auto url = L"http://" + m_serverUrl;
        if (url.find(L"http://") == std::wstring::npos && url.find(L"https://") == std::wstring::npos)
        {
            url = L"http://" + url;
        }

        OutputDebugStringW(L"[AIService] Request: ");
        OutputDebugStringW(endpoint.c_str());
        OutputDebugStringW(L"\n");

        STARTUPINFOW si{};
        si.cb = sizeof(si);
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_HIDE;

        PROCESS_INFORMATION pi{};
        SECURITY_ATTRIBUTES sa{};
        sa.nLength = sizeof(sa);
        sa.bInheritHandle = TRUE;

        HANDLE hReadPipe, hWritePipe;
        CreatePipe(&hReadPipe, &hWritePipe, &sa, 0);
        SetHandleInformation(hReadPipe, HANDLE_FLAG_INHERIT, 0);
        si.hStdOutput = hWritePipe;
        si.hStdError = hWritePipe;

        auto cmd = L"curl.exe -s -X POST \"" + url + endpoint + L"\" "
                   L"-H \"Content-Type: application/json\" "
                   L"-d \"" + body + L"\"";

        std::wstring result;
        if (CreateProcessW(nullptr, const_cast<wchar_t*>(cmd.c_str()),
                          nullptr, nullptr, TRUE, 0, nullptr, nullptr, &si, &pi))
        {
            CloseHandle(hWritePipe);

            char buffer[4096];
            DWORD bytesRead;
            while (ReadFile(hReadPipe, buffer, sizeof(buffer) - 1, &bytesRead, nullptr) && bytesRead > 0)
            {
                buffer[bytesRead] = '\0';
                result += std::wstring(buffer, buffer + bytesRead);
            }

            WaitForSingleObject(pi.hProcess, 60000);
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }

        CloseHandle(hReadPipe);
        return result;
    }

    std::wstring AIService::BuildPromptWithContext(hstring const& prompt, hstring const& context)
    {
        return L"Context:\n" + std::wstring(context) + L"\n\nQuestion: " + std::wstring(prompt);
    }

    event_token AIService::StatusChanged(Windows::Foundation::EventHandler<bool> const& handler)
    {
        return m_statusChangedHandler.add(handler);
    }

    void AIService::StatusChanged(event_token const& token) noexcept
    {
        m_statusChangedHandler.remove(token);
    }
}
