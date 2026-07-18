#pragma once

#include "App.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct App : AppT<App>
    {
        App();

    protected:
        void OnLaunched(Microsoft::UI::Xaml::LaunchActivatedEventArgs const& args) override;

    private:
        void InitializeTheme();
        bool IsSingleInstance();
        void HandleCommandLineArgs(winrt::array_view<winrt::hstring const> const& args);
        void OnUnhandledException(winrt::Windows::Foundation::IInspectable const& sender,
                                  Microsoft::UI::Xaml::UnhandledExceptionEventArgs const& args);

        std::mutex m_mutex;
        void* m_singleInstanceMutex{ nullptr };
    };
}
