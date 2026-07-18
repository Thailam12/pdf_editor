#pragma once

#include "MainWindow.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct MainWindow : MainWindowT<MainWindow>
    {
        MainWindow();

    protected:
        void OnNewTabClick(Windows::Foundation::IInspectable const& sender,
                           Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnDragOver(Windows::Foundation::IInspectable const& sender,
                        Microsoft::UI::Xaml::DragEventArgs const& args);
        void OnDrop(Windows::Foundation::IInspectable const& sender,
                    Microsoft::UI::Xaml::DragEventArgs const& args);
        void OnKeyDown(Windows::Foundation::IInspectable const& sender,
                       Microsoft::UI::Xaml::Input::KeyRoutedEventArgs const& args);

    private:
        void InitializeBackdrop();
        void InitializeTitleBar();
        void SetupKeyboardShortcuts();
        void LoadWindowState();
        void SaveWindowState();
        void CreateTab(std::wstring const& title, std::wstring const& filePath);
        void CloseTab(int index);
        void SwitchToTab(int index);

        std::vector<std::wstring> m_tabTitles;
        std::vector<std::wstring> m_tabFilePaths;
        int m_activeTabIndex{ -1 };
        std::mutex m_tabsMutex;
    };
}
