#pragma once

#include "Core/Application.g.h"

namespace winrt::PDFEditor::implementation
{
    struct Application : ApplicationT<Application>
    {
        Application();

        static Core::Application GetDefault();
        void Initialize();
        void Shutdown();
        bool IsInitialized() const;

        event_token PropertyChanged(Microsoft::UI::Xaml::Data::PropertyChangedEventHandler const& handler);
        void PropertyChanged(event_token const& token) noexcept;

    private:
        bool m_initialized{ false };
        std::wstring m_appDataPath;
        std::mutex m_mutex;

        void EnsureAppDataDirectory();
        void RegisterUnhandledExceptionHandler();
    };
}

namespace winrt::PDFEditor::factory_implementation
{
    struct Application : ApplicationT<Application, implementation::Application>
    {
    };
}
