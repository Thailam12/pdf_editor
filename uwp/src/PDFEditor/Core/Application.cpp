#include "pch.h"
#include "Core/Application.h"
#include "Core/Application.g.cpp"

namespace winrt::PDFEditor::implementation
{
    static std::shared_ptr<Application> s_instance{ nullptr };
    static std::mutex s_instanceMutex;

    Application::Application()
    {
        Initialize();
    }

    Core::Application Application::GetDefault()
    {
        std::lock_guard lock(s_instanceMutex);
        if (!s_instance)
        {
            s_instance = std::make_shared<Application>();
        }
        auto boxed = winrt::make<Application>();
        return boxed.as<Core::Application>();
    }

    void Application::Initialize()
    {
        std::lock_guard lock(m_mutex);
        if (m_initialized) return;

        try
        {
            EnsureAppDataDirectory();
            RegisterUnhandledExceptionHandler();
            m_initialized = true;

            OutputDebugStringW(L"[Application] Initialized successfully\n");
        }
        catch (winrt::hresult_error const& ex)
        {
            OutputDebugStringW(L"[Application] Initialization failed: ");
            OutputDebugStringW(ex.message().c_str());
            OutputDebugStringW(L"\n");
        }
    }

    void Application::Shutdown()
    {
        std::lock_guard lock(m_mutex);
        m_initialized = false;

        auto app = Microsoft::UI::Xaml::Application::Current();
        if (app)
        {
            app->Exit();
        }

        OutputDebugStringW(L"[Application] Shutdown complete\n");
    }

    bool Application::IsInitialized() const
    {
        return m_initialized;
    }

    void Application::EnsureAppDataDirectory()
    {
        auto appData = Windows::Storage::ApplicationData::Current();
        if (appData)
        {
            auto localFolder = appData.LocalFolder();
            m_appDataPath = localFolder.Path();
        }
        else
        {
            wchar_t* pPath = nullptr;
            if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_LocalAppData, 0, nullptr, &pPath)))
            {
                m_appDataPath = pPath;
                CoTaskMemFree(pPath);
            }
            else
            {
                m_appDataPath = L"C:\\PDFEditor";
            }
        }

        auto appDir = m_appDataPath + L"\\PDFEditorPro";
        if (!std::filesystem::exists(appDir))
        {
            std::filesystem::create_directories(appDir);
        }

        auto cacheDir = appDir + L"\\Cache";
        if (!std::filesystem::exists(cacheDir))
        {
            std::filesystem::create_directories(cacheDir);
        }

        auto thumbsDir = appDir + L"\\Thumbnails";
        if (!std::filesystem::exists(thumbsDir))
        {
            std::filesystem::create_directories(thumbsDir);
        }
    }

    void Application::RegisterUnhandledExceptionHandler()
    {
        SetUnhandledExceptionFilter([](LPEXCEPTION_POINTERS ep) -> LONG
        {
            OutputDebugStringW(L"[Application] Unhandled native exception\n");
            return EXCEPTION_EXECUTE_HANDLER;
        });
    }

    event_token Application::PropertyChanged(Microsoft::UI::Xaml::Data::PropertyChangedEventHandler const& handler)
    {
        return {};
    }

    void Application::PropertyChanged(event_token const& token) noexcept
    {
    }
}
