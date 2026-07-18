#include "pch.h"
#include "Services/PrintService.h"

using namespace winrt;

namespace winrt::PDFEditor::Services
{
    static std::shared_ptr<PrintService> s_instance{ nullptr };
    static std::mutex s_instanceMutex;

    PrintService::PrintService()
    {
    }

    PrintService PrintService::GetDefault()
    {
        std::lock_guard lock(s_instanceMutex);
        if (!s_instance)
        {
            s_instance = std::make_shared<PrintService>();
        }
        return *s_instance;
    }

    bool PrintService::PrintDocument(hstring const& filePath, PrintSettings const& settings)
    {
        auto args = BuildPrintArguments(filePath, settings);
        auto result = ExecutePrintCommand(args);

        OutputDebugStringW(L"[PrintService] Print: ");
        OutputDebugStringW(std::wstring(filePath).c_str());
        OutputDebugStringW(L"\n");

        return result;
    }

    bool PrintService::PrintPages(hstring const& filePath, std::vector<int> const& pageIndices,
                                   PrintSettings const& settings)
    {
        std::wstring pages;
        for (size_t i = 0; i < pageIndices.size(); ++i)
        {
            if (i > 0) pages += L",";
            pages += std::to_wstring(pageIndices[i] + 1);
        }

        auto modifiedSettings = settings;
        modifiedSettings.StartPage = 0;
        modifiedSettings.EndPage = -1;

        auto args = BuildPrintArguments(filePath, modifiedSettings);
        args += L" --pages \"" + pages + L"\"";

        return ExecutePrintCommand(args);
    }

    std::vector<hstring> PrintService::GetAvailablePrinters() const
    {
        std::vector<hstring> printers;

        DWORD bufferSize = 0;
        GetDefaultPrinterW(nullptr, &bufferSize);
        if (bufferSize > 0)
        {
            std::vector<wchar_t> buffer(bufferSize);
            if (GetDefaultPrinterW(buffer.data(), &bufferSize))
            {
                printers.push_back(buffer.data());
            }
        }

        PRINTER_INFO_2W* printerInfo = nullptr;
        DWORD bytesNeeded = 0;
        DWORD printerCount = 0;

        EnumPrintersW(PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS,
                      nullptr, 2, nullptr, 0, &bytesNeeded, &printerCount);

        if (bytesNeeded > 0)
        {
            std::vector<BYTE> buffer(bytesNeeded);
            if (EnumPrintersW(PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS,
                             nullptr, 2, buffer.data(), bytesNeeded, &bytesNeeded, &printerCount))
            {
                printerInfo = reinterpret_cast<PRINTER_INFO_2W*>(buffer.data());
                for (DWORD i = 0; i < printerCount; ++i)
                {
                    printers.push_back(printerInfo[i].pPrinterName);
                }
            }
        }

        return printers;
    }

    hstring PrintService::GetDefaultPrinter() const
    {
        DWORD bufferSize = 256;
        std::vector<wchar_t> buffer(bufferSize);
        if (GetDefaultPrinterW(buffer.data(), &bufferSize))
        {
            return hstring(buffer.data());
        }
        return L"";
    }

    bool PrintService::IsPrintingSupported() const
    {
        return GetAvailablePrinters().size() > 0;
    }

    void PrintService::ShowPrintDialog(hstring const& filePath)
    {
        STARTUPINFOW si{};
        si.cb = sizeof(si);
        PROCESS_INFORMATION pi{};

        auto fileArg = std::wstring(filePath);

        ShellExecuteW(nullptr, L"print", filePath.c_str(), nullptr, nullptr, SW_SHOW);
    }

    bool PrintService::ExecutePrintCommand(hstring const& command)
    {
        OutputDebugStringW(L"[PrintService] ");
        OutputDebugStringW(command.c_str());
        OutputDebugStringW(L"\n");

        STARTUPINFOW si{};
        si.cb = sizeof(si);
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_HIDE;

        PROCESS_INFORMATION pi{};

        if (CreateProcessW(nullptr, const_cast<wchar_t*>(command.c_str()),
                          nullptr, nullptr, FALSE, 0, nullptr, nullptr, &si, &pi))
        {
            WaitForSingleObject(pi.hProcess, 60000);

            DWORD exitCode = 0;
            GetExitCodeProcess(pi.hProcess, &exitCode);

            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);

            return exitCode == 0;
        }

        return false;
    }

    std::wstring PrintService::BuildPrintArguments(hstring const& filePath, PrintSettings const& settings)
    {
        auto args = L"sumatrapdf.exe -print-to \"" +
                    std::wstring(settings.PrinterName.empty() ? GetDefaultPrinter() : settings.PrinterName) +
                    L"\"";

        if (settings.StartPage > 0 || settings.EndPage > 0)
        {
            args += L" -print-range " + std::to_wstring(settings.StartPage + 1);
            if (settings.EndPage > settings.StartPage)
            {
                args += L"-" + std::to_wstring(settings.EndPage + 1);
            }
        }

        args += L" -print-settings \"" + std::to_wstring(settings.Copies) + L"x";

        if (settings.Duplex) args += L",duplex";
        if (!settings.Color) args += L",monochrome";
        if (settings.FitToPage) args += L",fit";

        args += L"\"";

        args += L" \"" + std::wstring(filePath) + L"\"";

        return args;
    }
}
