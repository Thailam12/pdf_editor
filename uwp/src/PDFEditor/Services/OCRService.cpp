#include "pch.h"
#include "Services/OCRService.h"

using namespace winrt;

namespace winrt::PDFEditor::Services
{
    static std::shared_ptr<OCRService> s_instance{ nullptr };
    static std::mutex s_instanceMutex;

    OCRService::OCRService()
    {
    }

    OCRService OCRService::GetDefault()
    {
        std::lock_guard lock(s_instanceMutex);
        if (!s_instance)
        {
            s_instance = std::make_shared<OCRService>();
        }
        return *s_instance;
    }

    winrt::Windows::Foundation::IAsyncOperation<hstring> OCRService::RecognizeTextAsync(int pageIndex)
    {
        co_await winrt::resume_background();

        auto cmd = L"ocr --page " + std::to_wstring(pageIndex) +
                   L" --language " + m_languageCode;
        auto result = ExecuteOCRCommand(cmd);

        {
            std::lock_guard lock(m_mutex);
            m_lastResults = ParseOCRResults(result);
        }

        std::wstring text;
        for (auto const& r : m_lastResults)
        {
            if (!text.empty()) text += L"\n";
            text += std::wstring(r.Text);
        }

        co_return hstring(text);
    }

    winrt::Windows::Foundation::IAsyncOperation<hstring> OCRService::RecognizeTextInRegionAsync(
        int pageIndex, double x, double y, double width, double height)
    {
        co_await winrt::resume_background();

        auto cmd = L"ocr_region --page " + std::to_wstring(pageIndex) +
                   L" --x " + std::to_wstring(x) +
                   L" --y " + std::to_wstring(y) +
                   L" --width " + std::to_wstring(width) +
                   L" --height " + std::to_wstring(height) +
                   L" --language " + m_languageCode;
        auto result = ExecuteOCRCommand(cmd);

        std::lock_guard lock(m_mutex);
        m_lastResults = ParseOCRResults(result);

        std::wstring text;
        for (auto const& r : m_lastResults)
        {
            if (!text.empty()) text += L"\n";
            text += std::wstring(r.Text);
        }

        co_return hstring(text);
    }

    std::vector<OCRResult> OCRService::GetDetailedResults() const
    {
        return m_lastResults;
    }

    bool OCRService::IsOCRAvailable() const
    {
        auto tessPath = std::filesystem::current_path() / L"tesseract" / L"tesseract.exe";
        return std::filesystem::exists(tessPath);
    }

    void OCRService::SetLanguage(hstring const& languageCode)
    {
        std::lock_guard lock(m_mutex);
        m_languageCode = std::wstring(languageCode);
    }

    hstring OCRService::GetLanguage() const
    {
        return m_languageCode;
    }

    std::wstring OCRService::ExecuteOCRCommand(std::wstring const& command)
    {
        auto exeDir = std::filesystem::current_path();
        auto tessPath = exeDir / L"tesseract" / L"tesseract.exe";

        auto cmdLine = L"\"" + tessPath.wstring() + L"\" " + command;

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

        std::wstring result;
        if (CreateProcessW(nullptr, const_cast<wchar_t*>(cmdLine.c_str()),
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

            WaitForSingleObject(pi.hProcess, 120000);
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }

        CloseHandle(hReadPipe);
        return result;
    }

    std::vector<OCRResult> OCRService::ParseOCRResults(std::wstring const& jsonResults)
    {
        std::vector<OCRResult> results;

        std::wistringstream stream(jsonResults);
        std::wstring line;
        while (std::getline(stream, line))
        {
            if (line.empty()) continue;

            OCRResult result;
            result.Text = hstring(line);
            result.Confidence = 1.0;
            result.X = 0;
            result.Y = 0;
            result.Width = 100;
            result.Height = 20;
            result.PageIndex = 0;
            results.push_back(result);
        }

        return results;
    }
}
