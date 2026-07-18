#include "pch.h"
#include "App.xaml.h"
#include "App.xaml.g.cpp"
#include "MainWindow.xaml.h"

#if defined _DEBUG && !defined DISABLE_XAML_GENERATED_BREAK_ON_UNHANDLED_EXCEPTION
extern "C" __declspec(dllimport) void __stdcall ResultFailureBoundary();
#endif

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;

namespace winrt::PDFEditor::implementation
{
    App::App()
    {
        InitializeComponent();

       UnhandledException([this](IInspectable const&, UnhandledExceptionEventArgs const& e)
        {
            e.Handled(true);
            auto message = e.Exception().Message();
            OutputDebugStringW(L"Unhandled Exception: ");
            OutputDebugStringW(message.c_str());
            OutputDebugStringW(L"\n");
        });

        Suspending([](IInspectable const&, Windows::ApplicationModel::SuspendingEventArgs const&) {});
        Resuming([](IInspectable const&, IInspectable const&) {});
    }

    bool App::IsSingleInstance()
    {
        m_singleInstanceMutex = CreateMutexW(nullptr, TRUE, L"PDFEditor_SingleInstance_{E4B7A5F2-9C3D-4E6B-8F1A-2D5C7E9B0A14}");
        if (GetLastError() == ERROR_ALREADY_EXISTS)
        {
            if (m_singleInstanceMutex)
            {
                ReleaseMutex(m_singleInstanceMutex);
                CloseHandle(m_singleInstanceMutex);
                m_singleInstanceMutex = nullptr;
            }
            return false;
        }
        return true;
    }

    void App::InitializeTheme()
    {
        auto root = Microsoft::UI::Xaml::ElementTheme::Dark;
        auto settings = Core::SettingsManager::GetDefault();
        if (settings)
        {
            auto themeStr = settings->GetTheme();
            if (themeStr == L"Light")
                root = Microsoft::UI::Xaml::ElementTheme::Light;
            else if (themeStr == L"System")
                root = Microsoft::UI::Xaml::ElementTheme::Default;
        }

        if (Root() && Root().Content())
        {
            Root().Content().RequestedTheme(root == Microsoft::UI::Xaml::ElementTheme::Default
                ? Microsoft::UI::Xaml::ElementTheme::Default
                : root);
        }
    }

    void App::HandleCommandLineArgs(winrt::array_view<winrt::hstring const> const& args)
    {
        if (args.size() > 1)
        {
            auto filePath = args[1];
            if (!filePath.empty() && std::filesystem::exists(std::wstring(filePath)))
            {
                auto docManager = Core::DocumentManager::GetDefault();
                if (docManager)
                {
                    docManager->OpenDocument(filePath);
                }
            }
        }
    }

    void App::OnLaunched(LaunchActivatedEventArgs const& args)
    {
        if (!IsSingleInstance())
        {
            auto app = Microsoft::UI::Xaml::Application::Current();
            if (app)
            {
                app->Exit();
            }
            return;
        }

        auto mainWindow = make<MainWindow>();
        mainWindow.Activate();

        InitializeTheme();

        auto cmdLine = GetCommandLineW();
        int argc = 0;
        auto argv = CommandLineToArgvW(cmdLine, &argc);
        if (argv && argc > 1)
        {
            std::vector<winrt::hstring> args;
            for (int i = 0; i < argc; ++i)
            {
                args.push_back(argv[i]);
            }
            HandleCommandLineArgs(args);
            LocalFree(argv);
        }
    }
}
