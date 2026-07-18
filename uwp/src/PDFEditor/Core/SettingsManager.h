#pragma once

#include "Core/SettingsManager.g.h"

namespace winrt::PDFEditor::implementation
{
    struct SettingsManager : SettingsManagerT<SettingsManager>
    {
        SettingsManager();

        static Core::SettingsManager GetDefault();

        hstring GetSetting(hstring const& key) const;
        void SetSetting(hstring const& key, hstring const& value);

        hstring GetTheme() const;
        void SetTheme(hstring const& theme);

        hstring GetLanguage() const;
        void SetLanguage(hstring const& language);

        double GetDefaultZoom() const;
        void SetDefaultZoom(double zoom);

        bool GetAutoSaveEnabled() const;
        void SetAutoSaveEnabled(bool enabled);

        uint32_t GetAutoSaveIntervalSeconds() const;
        void SetAutoSaveIntervalSeconds(uint32_t seconds);

        void Save();
        void Load();
        void ResetToDefaults();

    private:
        std::wstring m_settingsPath;
        std::unordered_map<std::wstring, std::wstring> m_settings;
        std::mutex m_mutex;

        void EnsureSettingsDirectory();
    };
}
