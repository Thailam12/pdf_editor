#include "pch.h"
#include "MainWindow.xaml.h"
#include "MainWindow.xaml.g.cpp"
#include "Core/DocumentManager.h"
#include "Core/SettingsManager.h"
#include "Views/EditorView.h"

using namespace winrt;
using namespace Microsoft::UI;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;
using namespace Microsoft::UI::Xaml::Input;
using namespace Microsoft::UI::Xaml::Media;
using namespace Windows::Foundation;
using namespace Windows::Foundation::Collections;
using namespace Windows::Graphics;

namespace winrt::PDFEditor::implementation
{
    MainWindow::MainWindow()
    {
        InitializeComponent();
        InitializeTitleBar();
        InitializeBackdrop();
        SetupKeyboardShortcuts();
        LoadWindowState();

        auto app = Application::Current();
        if (app)
        {
            app->UnhandledException([this](IInspectable const&, UnhandledExceptionEventArgs const& e)
            {
                e.Handled(true);
                if (StatusText())
                {
                    StatusText().Text(L"An error occurred");
                }
            });
        }
    }

    void MainWindow::InitializeTitleBar()
    {
        auto titleBar = TitleBar();
        if (titleBar)
        {
            ExtendsContentIntoTitleBar(true);
            SetTitleBar(titleBar);
        }

        auto windowNative = this->try_as<::IWindowNative>();
        if (windowNative)
        {
            HWND hwnd{ nullptr };
            windowNative->get_WindowHandle(&hwnd);
            if (hwnd)
            {
                auto title = L"PDF Editor Pro";
                SetWindowTextW(hwnd, title);

                DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                    &(BOOL{ TRUE }), sizeof(BOOL));
            }
        }
    }

    void MainWindow::InitializeBackdrop()
    {
        auto systemBackdrop = Microsoft::UI::Composition::SystemBackdrops::MicaSystemBackdrop();
        TrySetSystemBackdrop(systemBackdrop);
    }

    void MainWindow::SetupKeyboardShortcuts()
        {
        auto root = this->Content();
        if (!root) return;

        root->KeyDown([this](IInspectable const& sender, KeyRoutedEventArgs const& args)
        {
            auto ctrl = InputKeyboardSource::GetKeyStateForCurrentThread(Windows::System::VirtualKeyModifiers::Control);
            bool isCtrl = (ctrl & Input::VirtualKeyStates::Down) == Input::VirtualKeyStates::Down;
            auto shift = InputKeyboardSource::GetKeyStateForCurrentThread(Windows::System::VirtualKeyModifiers::Shift);
            bool isShift = (shift & Input::VirtualKeyStates::Down) == Input::VirtualKeyStates::Down;

            auto key = args.Key();

            if (isCtrl && key == Windows::System::VirtualKey::O)
            {
                auto docManager = Core::DocumentManager::GetDefault();
                if (docManager) docManager->PromptOpenDocument();
                args.Handled(true);
            }
            else if (isCtrl && key == Windows::System::VirtualKey::S)
            {
                auto docManager = Core::DocumentManager::GetDefault();
                if (docManager) docManager->SaveDocument();
                args.Handled(true);
            }
            else if (isCtrl && isShift && key == Windows::System::VirtualKey::S)
            {
                auto docManager = Core::DocumentManager::GetDefault();
                if (docManager) docManager->SaveDocumentAs();
                args.Handled(true);
            }
            else if (isCtrl && key == Windows::System::VirtualKey::N)
            {
                CreateNewDocument();
                args.Handled(true);
            }
            else if (isCtrl && key == Windows::System::VirtualKey::W)
            {
                if (m_activeTabIndex >= 0)
                    CloseTab(m_activeTabIndex);
                args.Handled(true);
            }
            else if (isCtrl && key == Windows::System::VirtualKey::Z)
            {
                auto docManager = Core::DocumentManager::GetDefault();
                if (docManager) docManager->Undo();
                args.Handled(true);
            }
            else if (isCtrl && key == Windows::System::VirtualKey::Y)
            {
                auto docManager = Core::DocumentManager::GetDefault();
                if (docManager) docManager->Redo();
                args.Handled(true);
            }
            else if (isCtrl && key == Windows::System::VirtualKey::F)
            {
                args.Handled(true);
            }
            else if (isCtrl && key == Windows::System::VirtualKey::P)
            {
                args.Handled(true);
            }
            else if (key == Windows::System::VirtualKey::F5)
            {
                args.Handled(true);
            }
        });
    }

    void MainWindow::LoadWindowState()
    {
        auto settings = Core::SettingsManager::GetDefault();
        if (settings)
        {
            auto width = settings->GetSetting(L"WindowWidth");
            auto height = settings->GetSetting(L"WindowHeight");
            auto left = settings->GetSetting(L"WindowLeft");
            auto top = settings->GetSetting(L"WindowTop");

            if (!width.empty() && !height.empty())
            {
                try
                {
                    AppWindow().Resize({ std::stoi(std::wstring(width)), std::stoi(std::wstring(height)) });
                }
                catch (...) {}
            }
        }
    }

    void MainWindow::SaveWindowState()
    {
        auto settings = Core::SettingsManager::GetDefault();
        if (settings)
        {
            auto bounds = AppWindow().Size();
            settings->SetSetting(L"WindowWidth", std::to_wstring(static_cast<int>(bounds.Width)));
            settings->SetSetting(L"WindowHeight", std::to_wstring(static_cast<int>(bounds.Height)));
        }
    }

    void MainWindow::CreateTab(std::wstring const& title, std::wstring const& filePath)
    {
        std::lock_guard lock(m_tabsMutex);
        m_tabTitles.push_back(title);
        m_tabFilePaths.push_back(filePath);

        auto tab = Microsoft::UI::Xaml::Controls::Button();
        tab.Content(winrt::box_value(title));
        tab.Height(28);
        tab.MinWidth(120);
        tab.MaxWidth(200);
        tab.Style(Microsoft::UI::Xaml::Application::Current()
            .FindResource(L"SubtleButtonStyle").as<Microsoft::UI::Xaml::Style>());

        auto index = static_cast<int>(m_tabTitles.size() - 1);
        tab.Click([this, index](IInspectable const&, RoutedEventArgs const&)
        {
            SwitchToTab(index);
        });

        TabStrip().Children().Append(tab);
        SwitchToTab(static_cast<int>(m_tabTitles.size() - 1));

        if (EmptyState())
            EmptyState().Visibility(Visibility::Collapsed);
    }

    void MainWindow::CloseTab(int index)
    {
        std::lock_guard lock(m_tabsMutex);
        if (index < 0 || index >= static_cast<int>(m_tabTitles.size()))
            return;

        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager)
        {
            docManager->CloseDocument(index);
        }

        m_tabTitles.erase(m_tabTitles.begin() + index);
        m_tabFilePaths.erase(m_tabFilePaths.begin() + index);

        if (TabStrip() && index < static_cast<int>(TabStrip().Children().Size()))
        {
            TabStrip().Children().RemoveAt(index);
        }

        if (m_tabTitles.empty())
        {
            if (EmptyState())
                EmptyState().Visibility(Visibility::Visible);
            m_activeTabIndex = -1;
        }
        else
        {
            SwitchToTab(std::min(index, static_cast<int>(m_tabTitles.size()) - 1));
        }
    }

    void MainWindow::SwitchToTab(int index)
    {
        if (index < 0 || index >= static_cast<int>(m_tabTitles.size()))
            return;

        m_activeTabIndex = index;

        auto tabs = TabStrip();
        if (!tabs) return;

        for (uint32_t i = 0; i < tabs.Children().Size(); ++i)
        {
            auto btn = tabs.Children().GetAt(i).as<Button>();
            if (btn)
            {
                if (static_cast<int>(i) == index)
                {
                    btn.Style(Application::Current().FindResource(L"AccentButtonStyle").as<Style>());
                }
                else
                {
                    btn.Style(Application::Current().FindResource(L"SubtleButtonStyle").as<Style>());
                }
            }
        }

        auto title = m_tabTitles[index];
        auto windowNative = this->try_as<::IWindowNative>();
        if (windowNative)
        {
            HWND hwnd{ nullptr };
            windowNative->get_WindowHandle(&hwnd);
            if (hwnd)
            {
                auto fullTitle = title + L" - PDF Editor Pro";
                SetWindowTextW(hwnd, fullTitle.c_str());
            }
        }

        if (StatusText())
        {
            StatusText().Text(L"Editing: " + winrt::hstring(title));
        }
    }

    void MainWindow::OpenFile(hstring const& filePath)
    {
        std::wstring path(filePath);
        auto title = std::filesystem::path(path).filename().wstring();
        CreateTab(title, path);

        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager)
        {
            docManager->OpenDocument(filePath);
        }
    }

    void MainWindow::CreateNewDocument()
    {
        CreateTab(L"Untitled", L"");
    }

    void MainWindow::SaveCurrentDocument()
    {
        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager) docManager->SaveDocument();
    }

    void MainWindow::SaveCurrentDocumentAs()
    {
        auto docManager = Core::DocumentManager::GetDefault();
        if (docManager) docManager->SaveDocumentAs();
    }

    void MainWindow::OnNewTabClick(IInspectable const&, RoutedEventArgs const&)
    {
        CreateNewDocument();
    }

    void MainWindow::OnDragOver(IInspectable const&, DragEventArgs const& args)
    {
        auto dataView = args.DataView();
        if (dataView.Contains(Windows::ApplicationModel::DataTransfer::StandardDataFormats::StorageItems()))
        {
            args.DragUIOverride().Caption(L"Open PDF");
            args.DragUIOverride().IsCaptionVisible(true);
            args.DragUIOverride().IsContentVisible(true);
            args.AcceptedOperation(Windows::ApplicationModel::DataTransfer::DataPackageOperation::Copy);
        }
    }

    void MainWindow::OnDrop(IInspectable const&, DragEventArgs const& args)
    {
        auto dataView = args.DataView();
        if (dataView.Contains(Windows::ApplicationModel::DataTransfer::StandardDataFormats::StorageItems()))
        {
            auto asyncOp = dataView.GetStorageItemsAsync();
            asyncOp.Completed([this](auto const& op, auto const&)
            {
                auto items = op.GetResults();
                for (auto const& item : items)
                {
                    auto storageFile = item.as<Windows::Storage::StorageFile>();
                    if (storageFile)
                    {
                        auto path = storageFile.Path();
                        if (path.ends_with(L".pdf") || path.ends_with(L".PDF"))
                        {
                            RunOnUIThread([this, path]()
                            {
                                OpenFile(path);
                            });
                        }
                    }
                }
            });
        }
    }

    void MainWindow::OnKeyDown(IInspectable const&, KeyRoutedEventArgs const& args)
    {
    }
}
