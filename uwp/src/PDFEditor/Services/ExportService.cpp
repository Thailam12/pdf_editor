#include "pch.h"
#include "Services/ExportService.h"

using namespace winrt;

namespace winrt::PDFEditor::Services
{
    static std::shared_ptr<ExportService> s_instance{ nullptr };
    static std::mutex s_instanceMutex;

    ExportService::ExportService()
    {
    }

    ExportService ExportService::GetDefault()
    {
        std::lock_guard lock(s_instanceMutex);
        if (!s_instance)
        {
            s_instance = std::make_shared<ExportService>();
        }
        return *s_instance;
    }

    bool ExportService::ExportDocument(hstring const& sourcePath, hstring const& outputPath, ExportFormat format)
    {
        if (!ValidateOutputPath(outputPath)) return false;

        auto cmd = L"export --source \"" + std::wstring(sourcePath) +
                   L"\" --output \"" + std::wstring(outputPath) +
                   L"\" --format " + GetFormatExtension(format);
        auto result = ExecuteExportCommand(cmd);

        OutputDebugStringW(L"[ExportService] Export: ");
        OutputDebugStringW(std::wstring(sourcePath).c_str());
        OutputDebugStringW(L" -> ");
        OutputDebugStringW(std::wstring(outputPath).c_str());
        OutputDebugStringW(L"\n");

        return !result.empty();
    }

    bool ExportService::ExportPage(int pageIndex, hstring const& outputPath, ExportFormat format, int dpi)
    {
        if (!ValidateOutputPath(outputPath)) return false;

        auto cmd = L"export_page --page " + std::to_wstring(pageIndex) +
                   L" --output \"" + std::wstring(outputPath) +
                   L"\" --format " + GetFormatExtension(format) +
                   L" --dpi " + std::to_wstring(dpi);
        auto result = ExecuteExportCommand(cmd);
        return !result.empty();
    }

    bool ExportService::ExportPages(std::vector<int> const& pageIndices, hstring const& outputDir,
                                     ExportFormat format, int dpi)
    {
        std::wstring pages;
        for (size_t i = 0; i < pageIndices.size(); ++i)
        {
            if (i > 0) pages += L",";
            pages += std::to_wstring(pageIndices[i]);
        }

        auto cmd = L"export_pages --pages \"" + pages +
                   L"\" --output_dir \"" + std::wstring(outputDir) +
                   L"\" --format " + GetFormatExtension(format) +
                   L" --dpi " + std::to_wstring(dpi);
        auto result = ExecuteExportCommand(cmd);
        return !result.empty();
    }

    bool ExportService::ConvertToImage(hstring const& pdfPath, hstring const& outputDir, int dpi)
    {
        auto cmd = L"convert_to_images --source \"" + std::wstring(pdfPath) +
                   L"\" --output_dir \"" + std::wstring(outputDir) +
                   L"\" --dpi " + std::to_wstring(dpi);
        auto result = ExecuteExportCommand(cmd);
        return !result.empty();
    }

    bool ExportService::ConvertToText(hstring const& pdfPath, hstring const& outputPath)
    {
        auto cmd = L"convert_to_text --source \"" + std::wstring(pdfPath) +
                   L"\" --output \"" + std::wstring(outputPath) + L"\"";
        auto result = ExecuteExportCommand(cmd);
        return !result.empty();
    }

    bool ExportService::ConvertToHTML(hstring const& pdfPath, hstring const& outputPath)
    {
        auto cmd = L"convert_to_html --source \"" + std::wstring(pdfPath) +
                   L"\" --output \"" + std::wstring(outputPath) + L"\"";
        auto result = ExecuteExportCommand(cmd);
        return !result.empty();
    }

    bool ExportService::ConvertToDOCX(hstring const& pdfPath, hstring const& outputPath)
    {
        auto cmd = L"convert_to_docx --source \"" + std::wstring(pdfPath) +
                   L"\" --output \"" + std::wstring(outputPath) + L"\"";
        auto result = ExecuteExportCommand(cmd);
        return !result.empty();
    }

    std::vector<hstring> ExportService::GetSupportedFormats() const
    {
        return {
            L"PDF", L"PNG", L"JPEG", L"TIFF", L"BMP",
            L"SVG", L"Text", L"HTML", L"DOCX", L"XPS", L"PostScript"
        };
    }

    hstring ExportService::GetFormatExtension(ExportFormat format) const
    {
        switch (format)
        {
        case ExportFormat::PDF: return L"pdf";
        case ExportFormat::PNG: return L"png";
        case ExportFormat::JPEG: return L"jpg";
        case ExportFormat::TIFF: return L"tiff";
        case ExportFormat::BMP: return L"bmp";
        case ExportFormat::SVG: return L"svg";
        case ExportFormat::Text: return L"txt";
        case ExportFormat::HTML: return L"html";
        case ExportFormat::DOCX: return L"docx";
        case ExportFormat::XPS: return L"xps";
        case ExportFormat::PostScript: return L"ps";
        default: return L"pdf";
        }
    }

    bool ExportService::ValidateOutputPath(hstring const& outputPath)
    {
        auto path = std::filesystem::path(std::wstring(outputPath));
        auto parent = path.parent_path();
        if (!parent.empty() && !std::filesystem::exists(parent))
        {
            try
            {
                std::filesystem::create_directories(parent);
            }
            catch (...)
            {
                return false;
            }
        }
        return true;
    }

    std::wstring ExportService::ExecuteExportCommand(std::wstring const& command)
    {
        OutputDebugStringW(L"[ExportService] ");
        OutputDebugStringW(command.c_str());
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

        auto exeDir = std::filesystem::current_path();
        auto pythonPath = exeDir / L"python" / L"python.exe";
        auto cmdLine = L"\"" + pythonPath.wstring() + L"\" scripts/pdf_engine.py " + command;

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

            WaitForSingleObject(pi.hProcess, 60000);
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }

        CloseHandle(hReadPipe);
        return result;
    }
}
