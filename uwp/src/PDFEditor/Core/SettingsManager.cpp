#include "pch.h"
#include "Core/SettingsManager.h"
#include "Core/SettingsManager.g.cpp"

using namespace winrt;

namespace winrt::PDFEditor::implementation
{
    static std::shared_ptr<SettingsManager> s_instance{ nullptr };
    static std::mutex s_instanceMutex;

    SettingsManager::SettingsManager()
    {
        EnsureSettingsDirectory();
        Load();
    }

    Core::SettingsManager SettingsManager::GetDefault()
    {
        std::lock_guard lock(s_instanceMutex);
        if (!s_instance)
        {
            s_instance = std::make_shared<SettingsManager>();
        }
        auto boxed = winrt::make<SettingsManager>();
        return boxed.as<Core::SettingsManager>();
    }

    hstring SettingsManager::GetSetting(hstring const& key) const
    {
        std::lock_guard lock(m_mutex);
        auto it = m_settings.find(std::wstring(key));
        if (it != m_settings.end())
        {
            return it->second;
        }
        return L"";
    }

    void SettingsManager::SetSetting(hstring const& key, hstring const& value)
    {
        std::lock_guard lock(m_mutex);
        m_settings[std::wstring(key)] = std::wstring(value);
    }

    hstring SettingsManager::GetTheme() const
    {
        auto val = GetSetting(L"Theme");
        return val.empty() ? L"Dark" : val;
    }

    void SettingsManager::SetTheme(hstring const& theme)
    {
        SetSetting(L"Theme", theme);
        Save();
    }

    hstring SettingsManager::GetLanguage() const
    {
        auto val = GetSetting(L"Language");
        return val.empty() ? L"en-US" : val;
    }

    void SettingsManager::SetLanguage(hstring const& language)
    {
        SetSetting(L"Language", language);
        Save();
    }

    double SettingsManager::GetDefaultZoom() const
    {
        auto val = GetSetting(L"DefaultZoom");
        if (val.empty()) return 100.0;
        try { return std::stod(std::wstring(val)); }
        catch (...) { return 100.0; }
    }

    void SettingsManager::SetDefaultZoom(double zoom)
    {
        SetSetting(L"DefaultZoom", std::to_wstring(zoom));
        Save();
    }

    bool SettingsManager::GetAutoSaveEnabled() const
    {
        auto val = GetSetting(L"AutoSaveEnabled");
        return val == L"true" || val.empty();
    }

    void SettingsManager::SetAutoSaveEnabled(bool enabled)
    {
        SetSetting(L"AutoSaveEnabled", enabled ? L"true" : L"false");
        Save();
    }

    uint32_t SettingsManager::GetAutoSaveIntervalSeconds() const
    {
        auto val = GetSetting(L"AutoSaveInterval");
        if (val.empty()) return 300;
        try { return static_cast<uint32_t>(std::stoul(std::wstring(val))); }
        catch (...) { return 300; }
    }

    void SettingsManager::SetAutoSaveIntervalSeconds(uint32_t seconds)
    {
        SetSetting(L"AutoSaveInterval", std::to_wstring(seconds));
        Save();
    }

    void SettingsManager::Save()
    {
        std::lock_guard lock(m_mutex);

        try
        {
            std::wofstream file(m_settingsPath, std::ios::out | std::ios::binary);
            if (!file.is_open()) return;

            file << L"{\n";
            bool first = true;
            for (auto const& [key, value] : m_settings)
            {
                if (!first) file << L",\n";
                first = false;
                file << L"  \"" << key << L"\": \"" << value << L"\"";
            }
            file << L"\n}\n";
            file.close();
        }
        catch (...)
        {
            OutputDebugStringW(L"[SettingsManager] Failed to save settings\n");
        }
    }

    void SettingsManager::Load()
    {
        std::lock_guard lock(m_mutex);
        m_settings.clear();

        try
        {
            std::wifstream file(m_settingsPath);
            if (!file.is_open())
            {
                ResetToDefaults();
                return;
            }

            std::wstring line;
            while (std::getline(file, line))
            {
                auto colonPos = line.find(L':');
                if (colonPos == std::wstring::npos) continue;

                auto keyPart = line.substr(0, colonPos);
                auto valuePart = line.substr(colonPos + 1);

                auto trim = [](std::wstring& s)
                {
                    while (!s.empty() && (s.front() == L' ' || s.front() == L'\t')) s.erase(s.begin());
                    while (!s.empty() && (s.back() == L' ' || s.back() == L'\t')) s.pop_back();
                };

                trim(keyPart);
                trim(valuePart);

                if (!keyPart.empty() && keyPart.front() == L'"')
                    keyPart = keyPart.substr(1);
                if (!keyPart.empty() && keyPart.back() == L'"')
                    keyPart.pop_back();

                if (!valuePart.empty() && valuePart.front() == L'"')
                    valuePart = valuePart.substr(1);
                if (!valuePart.empty() && valuePart.back() == L'"')
                    valuePart.pop_back();

                auto commaPos = valuePart.find(L',');
                if (commaPos != std::wstring::npos)
                    valuePart = valuePart.substr(0, commaPos);

                auto endBrace = valuePart.find(L'}');
                if (endBrace != std::wstring::npos)
                    valuePart = valuePart.substr(0, endBrace);

                trim(keyPart);
                trim(valuePart);

                if (!keyPart.empty())
                {
                    m_settings[keyPart] = valuePart;
                }
            }
        }
        catch (...)
        {
            OutputDebugStringW(L"[SettingsManager] Failed to load settings, using defaults\n");
            ResetToDefaults();
        }
    }

    void SettingsManager::ResetToDefaults()
    {
        m_settings.clear();
        m_settings[L"Theme"] = L"Dark";
        m_settings[L"Language"] = L"en-US";
        m_settings[L"DefaultZoom"] = L"100.0";
        m_settings[L"AutoSaveEnabled"] = L"true";
        m_settings[L"AutoSaveInterval"] = L"300";
        m_settings[L"WindowWidth"] = L"1400";
        m_settings[L"WindowHeight"] = L"900";
        m_settings[L"ShowThumbnails"] = L"true";
        m_settings[L"ShowProperties"] = L"true";
        m_settings[L"ShowAI"] = L"false";
        m_settings[L"ToolbarSize"] = L"Medium";
        m_settings[L"RecentFileCount"] = L"0";
        m_settings[L"DefaultExportFormat"] = L"PDF";
        m_settings[L"DefaultPageLayout"] = L"SinglePage";
        m_settings[L"EnableSpellCheck"] = L"true";
        m_settings[L"EnableAutoCorrect"] = L"false";
        m_settings[L"MeasurementUnit"] = L"Millimeters";
        m_settings[L"ShowGridLines"] = L"false";
        m_settings[L"SnapToGrid"] = L"false";
        m_settings[L"HighQualityRendering"] = L"true";

        Save();
    }

    void SettingsManager::EnsureSettingsDirectory()
    {
        try
        {
            wchar_t* pPath = nullptr;
            if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_LocalAppData, 0, nullptr, &pPath)))
            {
                m_settingsPath = std::wstring(pPath) + L"\\PDFEditorPro\\settings.json";
                CoTaskMemFree(pPath);
            }
            else
            {
                m_settingsPath = L"C:\\PDFEditor\\settings.json";
            }

            auto dir = std::filesystem::path(m_settingsPath).parent_path();
            if (!std::filesystem::exists(dir))
            {
                std::filesystem::create_directories(dir);
            }
        }
        catch (...)
        {
            m_settingsPath = L"settings.json";
        }
    }
}
