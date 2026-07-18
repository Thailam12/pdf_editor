#include "pch.h"
#include "Services/PDFService.h"

using namespace winrt;

namespace winrt::PDFEditor::Services
{
    static std::shared_ptr<PDFService> s_instance{ nullptr };
    static std::mutex s_instanceMutex;

    PDFService::PDFService()
    {
    }

    PDFService PDFService::GetDefault()
    {
        std::lock_guard lock(s_instanceMutex);
        if (!s_instance)
        {
            s_instance = std::make_shared<PDFService>();
        }
        return *s_instance;
    }

    bool PDFService::OpenDocument(hstring const& filePath)
    {
        std::lock_guard lock(m_mutex);

        auto path = std::wstring(filePath);
        if (!std::filesystem::exists(path))
        {
            OutputDebugStringW(L"[PDFService] File not found: ");
            OutputDebugStringW(path.c_str());
            OutputDebugStringW(L"\n");
            return false;
        }

        m_currentDocumentPath = path;
        m_pageCount = 1;
        m_isModified = false;

        auto cmd = L"open --file \"" + path + L"\"";
        auto result = ExecutePythonCommand(cmd);

        OutputDebugStringW(L"[PDFService] Opened: ");
        OutputDebugStringW(path.c_str());
        OutputDebugStringW(L"\n");

        return true;
    }

    bool PDFService::SaveDocument(hstring const& filePath)
    {
        std::lock_guard lock(m_mutex);
        auto path = std::wstring(filePath);
        if (path.empty()) path = m_currentDocumentPath;
        if (path.empty()) return false;

        auto cmd = L"save --file \"" + path + L"\"";
        auto result = ExecutePythonCommand(cmd);
        m_isModified = false;

        OutputDebugStringW(L"[PDFService] Saved: ");
        OutputDebugStringW(path.c_str());
        OutputDebugStringW(L"\n");

        return true;
    }

    bool PDFService::SaveDocumentAs(hstring const& filePath)
    {
        std::lock_guard lock(m_mutex);
        auto cmd = L"save_as --source \"" + m_currentDocumentPath + L"\" --target \"" + std::wstring(filePath) + L"\"";
        auto result = ExecutePythonCommand(cmd);

        if (!result.empty())
        {
            m_currentDocumentPath = std::wstring(filePath);
            m_isModified = false;
        }

        return !result.empty();
    }

    void PDFService::CloseDocument()
    {
        std::lock_guard lock(m_mutex);

        if (!m_currentDocumentPath.empty() && m_isModified)
        {
            ExecutePythonCommand(L"save --file \"" + m_currentDocumentPath + L"\"");
        }

        ExecutePythonCommand(L"close");
        m_currentDocumentPath.clear();
        m_pageCount = 0;
        m_isModified = false;
    }

    int PDFService::GetPageCount() const
    {
        return m_pageCount;
    }

    winrt::Windows::Foundation::IAsyncAction PDFService::RenderPage(int pageIndex, int width, int height)
    {
        co_await winrt::resume_background();
        auto cmd = L"render --page " + std::to_wstring(pageIndex) +
                   L" --width " + std::to_wstring(width) +
                   L" --height " + std::to_wstring(height);
        ExecutePythonCommand(cmd);
    }

    std::vector<hstring> PDFService::SearchText(hstring const& query, bool matchCase, bool wholeWord)
    {
        auto cmd = L"search --query \"" + std::wstring(query) + L"\"" +
                   (matchCase ? L" --match-case" : L"") +
                   (wholeWord ? L" --whole-word" : L"");

        auto result = ExecutePythonCommand(cmd);

        std::vector<hstring> results;
        std::wistringstream stream(result);
        std::wstring line;
        while (std::getline(stream, line))
        {
            if (!line.empty())
            {
                results.push_back(line);
            }
        }

        return results;
    }

    bool PDFService::InsertText(int pageIndex, double x, double y, hstring const& text,
                                 hstring const& fontName, double fontSize)
    {
        auto cmd = L"insert_text --page " + std::to_wstring(pageIndex) +
                   L" --x " + std::to_wstring(x) +
                   L" --y " + std::to_wstring(y) +
                   L" --text \"" + std::wstring(text) + L"\"" +
                   L" --font \"" + std::wstring(fontName) + L"\"" +
                   L" --size " + std::to_wstring(fontSize);
        auto result = ExecutePythonCommand(cmd);
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::DeleteElement(int pageIndex, hstring const& elementId)
    {
        auto cmd = L"delete_element --page " + std::to_wstring(pageIndex) +
                   L" --id \"" + std::wstring(elementId) + L"\"";
        auto result = ExecutePythonCommand(cmd);
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::MoveElement(int pageIndex, hstring const& elementId, double newX, double newY)
    {
        auto cmd = L"move_element --page " + std::to_wstring(pageIndex) +
                   L" --id \"" + std::wstring(elementId) + L"\"" +
                   L" --x " + std::to_wstring(newX) +
                   L" --y " + std::to_wstring(newY);
        auto result = ExecutePythonCommand(cmd);
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::AddAnnotation(int pageIndex, hstring const& type, double x, double y,
                                    double width, double height, hstring const& content)
    {
        auto cmd = L"add_annotation --page " + std::to_wstring(pageIndex) +
                   L" --type \"" + std::wstring(type) + L"\"" +
                   L" --x " + std::to_wstring(x) +
                   L" --y " + std::to_wstring(y) +
                   L" --width " + std::to_wstring(width) +
                   L" --height " + std::to_wstring(height) +
                   L" --content \"" + std::wstring(content) + L"\"";
        auto result = ExecutePythonCommand(cmd);
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::RemoveAnnotation(int pageIndex, hstring const& annotationId)
    {
        auto cmd = L"remove_annotation --page " + std::to_wstring(pageIndex) +
                   L" --id \"" + std::wstring(annotationId) + L"\"";
        auto result = ExecutePythonCommand(cmd);
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::InsertPage(int position)
    {
        auto cmd = L"insert_page --position " + std::to_wstring(position);
        auto result = ExecutePythonCommand(cmd);
        if (!result.empty()) m_pageCount++;
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::DeletePage(int pageIndex)
    {
        auto cmd = L"delete_page --page " + std::to_wstring(pageIndex);
        auto result = ExecutePythonCommand(cmd);
        if (!result.empty()) m_pageCount--;
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::RotatePage(int pageIndex, int degrees)
    {
        auto cmd = L"rotate_page --page " + std::to_wstring(pageIndex) +
                   L" --degrees " + std::to_wstring(degrees);
        auto result = ExecutePythonCommand(cmd);
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::CropPage(int pageIndex, double left, double top, double width, double height)
    {
        auto cmd = L"crop_page --page " + std::to_wstring(pageIndex) +
                   L" --left " + std::to_wstring(left) +
                   L" --top " + std::to_wstring(top) +
                   L" --width " + std::to_wstring(width) +
                   L" --height " + std::to_wstring(height);
        auto result = ExecutePythonCommand(cmd);
        m_isModified = true;
        return !result.empty();
    }

    bool PDFService::ExtractPages(std::vector<int> const& pageIndices, hstring const& outputPath)
    {
        std::wstring pages;
        for (size_t i = 0; i < pageIndices.size(); ++i)
        {
            if (i > 0) pages += L",";
            pages += std::to_wstring(pageIndices[i]);
        }
        auto cmd = L"extract_pages --pages \"" + pages + L"\" --output \"" + std::wstring(outputPath) + L"\"";
        auto result = ExecutePythonCommand(cmd);
        return !result.empty();
    }

    bool PDFService::MergeDocuments(std::vector<hstring> const& filePaths)
    {
        std::wstring files;
        for (size_t i = 0; i < filePaths.size(); ++i)
        {
            if (i > 0) files += L";";
            files += std::wstring(filePaths[i]);
        }
        auto cmd = L"merge --files \"" + files + L"\"";
        auto result = ExecutePythonCommand(cmd);
        return !result.empty();
    }

    bool PDFService::SplitDocument(std::vector<int> const& splitPoints, hstring const& outputDir)
    {
        std::wstring points;
        for (size_t i = 0; i < splitPoints.size(); ++i)
        {
            if (i > 0) points += L",";
            points += std::to_wstring(splitPoints[i]);
        }
        auto cmd = L"split --points \"" + points + L"\" --output_dir \"" + std::wstring(outputDir) + L"\"";
        auto result = ExecutePythonCommand(cmd);
        return !result.empty();
    }

    winrt::Windows::Foundation::IAsyncAction PDFService::GetPageThumbnail(int pageIndex, int width, int height)
    {
        co_await winrt::resume_background();
        auto cmd = L"thumbnail --page " + std::to_wstring(pageIndex) +
                   L" --width " + std::to_wstring(width) +
                   L" --height " + std::to_wstring(height);
        ExecutePythonCommand(cmd);
    }

    std::wstring PDFService::ExecutePythonCommand(std::wstring const& command)
    {
        auto pythonPath = GetPythonExecutablePath();
        auto scriptPath = L"scripts/pdf_engine.py";

        auto fullCmd = L"\" " + pythonPath + L" \" " + scriptPath + L" " + command;

        OutputDebugStringW(L"[PDFService] Executing: ");
        OutputDebugStringW(fullCmd.c_str());
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

        std::wstring result;
        if (CreateProcessW(nullptr, const_cast<wchar_t*>(fullCmd.c_str()),
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

            WaitForSingleObject(pi.hProcess, 30000);
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }

        CloseHandle(hReadPipe);
        return result;
    }

    std::wstring PDFService::GetPythonExecutablePath() const
    {
        auto exeDir = std::filesystem::current_path();
        auto pythonPath = exeDir / "python" / "python.exe";
        if (std::filesystem::exists(pythonPath))
        {
            return pythonPath.wstring();
        }

        pythonPath = exeDir / "python3.exe";
        if (std::filesystem::exists(pythonPath))
        {
            return pythonPath.wstring();
        }

        return L"python";
    }
}
