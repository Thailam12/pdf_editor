#pragma once

#include "Views/AIView.g.h"
#include "pch.h"

namespace winrt::PDFEditor::implementation
{
    struct AIView : AIViewT<AIView>
    {
        AIView();

        void SendQuery(hstring const& query);
        void ClearChat();

    protected:
        void OnCloseClick(Windows::Foundation::IInspectable const& sender,
                          Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnSummarizeClick(Windows::Foundation::IInspectable const& sender,
                              Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnTranslateClick(Windows::Foundation::IInspectable const& sender,
                              Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnRedactClick(Windows::Foundation::IInspectable const& sender,
                           Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnSendClick(Windows::Foundation::IInspectable const& sender,
                         Microsoft::UI::Xaml::RoutedEventArgs const& args);
        void OnQueryKeyDown(Windows::Foundation::IInspectable const& sender,
                            Microsoft::UI::Xaml::Input::KeyRoutedEventArgs const& args);

    private:
        void AppendMessage(hstring const& role, hstring const& content);
        void ShowTypingIndicator();
        void HideTypingIndicator();
        winrt::Windows::Foundation::IAsyncAction ProcessQuery(hstring const& query);

        std::vector<std::pair<std::wstring, std::wstring>> m_conversationHistory;
    };
}
