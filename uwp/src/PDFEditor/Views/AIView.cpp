#include "pch.h"
#include "Views/AIView.h"
#include "Views/AIView.g.cpp"

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;

namespace winrt::PDFEditor::implementation
{
    AIView::AIView()
    {
        InitializeComponent();
    }

    void AIView::SendQuery(hstring const& query)
    {
        if (query.empty()) return;

        if (WelcomeMessage())
        {
            auto msg = WelcomeMessage();
            ChatMessages().Children().RemoveAt(0);
        }

        AppendMessage(L"user", std::wstring(query));
        ShowTypingIndicator();
        ProcessQuery(std::wstring(query));
    }

    void AIView::ClearChat()
    {
        m_conversation_history.clear();
        ChatMessages().Children().Clear();
    }

    void AIView::OnCloseClick(IInspectable const&, RoutedEventArgs const&)
    {
        this->Visibility(Visibility::Collapsed);
    }

    void AIView::OnSummarizeClick(IInspectable const&, RoutedEventArgs const&)
    {
        SendQuery(L"Please summarize this PDF document. Provide key points, main topics, and a brief overview.");
    }

    void AIView::OnTranslateClick(IInspectable const&, RoutedEventArgs const&)
    {
        SendQuery(L"Translate this document to English, maintaining the original formatting and meaning.");
    }

    void AIView::OnRedactClick(IInspectable const&, RoutedEventArgs const&)
    {
        SendQuery(L"Identify any sensitive information in this document that should be redacted (names, SSNs, credit cards, addresses, etc.)");
    }

    void AIView::OnSendClick(IInspectable const&, RoutedEventArgs const&)
    {
        if (QueryInput())
        {
            auto query = QueryInput().Text();
            if (!query.empty())
            {
                SendQuery(query);
                QueryInput().Text(L"");
            }
        }
    }

    void AIView::OnQueryKeyDown(IInspectable const&, Input::KeyRoutedEventArgs const& args)
    {
        if (args.Key() == Windows::System::VirtualKey::Enter)
        {
            OnSendClick(nullptr, RoutedEventArgs());
            args.Handled(true);
        }
    }

    void AIView::AppendMessage(hstring const& role, std::wstring const& content)
    {
        m_conversation_history.push_back({ std::wstring(role), content });

        auto card = Grid();
        auto margin = Thickness{ 8, 4, 8, 4 };
        card.Margin(margin);

        auto border = Border();
        border.CornerRadius(Microsoft::UI::Xaml::CornerRadiusHelper::FromCornerRadius(8, 8, 8, 8));
        border.Padding(Thickness{ 12, 8, 12, 8 });

        if (std::wstring(role) == L"user")
        {
            border.Background(SolidColorBrush(Windows::UI::ColorHelper::FromArgb(40, 0, 120, 212)));
            border.HorizontalAlignment(HorizontalAlignment::Right);
        }
        else
        {
            border.Background(SolidColorBrush(Windows::UI::ColorHelper::FromArgb(25, 128, 128, 128)));
            border.HorizontalAlignment(HorizontalAlignment::Left);
        }

        auto textBlock = TextBlock();
        textBlock.Text(winrt::hstring(content));
        textBlock.TextWrapping(TextWrapping::Wrap);
        textBlock.Style(Application::Current().FindResource(L"BodyTextBlockStyle").as<Style>());
        textBlock.MaxWidth(340);

        border.Child(textBlock);
        card.Children().Append(border);

        ChatMessages().Children().Append(card);

        if (ChatScroll())
        {
            ChatScroll().ScrollToEnd();
        }
    }

    void AIView::ShowTypingIndicator()
    {
        if (StatusText())
        {
            StatusText().Text(L"Thinking...");
        }
        if (StatusDot())
        {
            StatusDot().Fill(SolidColorBrush(Windows::UI::ColorHelper::FromArgb(255, 255, 165, 0)));
        }
    }

    void AIView::HideTypingIndicator()
    {
        if (StatusText())
        {
            StatusText().Text(L"PDFMind 100M Ready");
        }
        if (StatusDot())
        {
            StatusDot().Fill(SolidColorBrush(Windows::UI::ColorHelper::FromArgb(255, 0, 120, 212)));
        }
    }

    winrt::Windows::Foundation::IAsyncAction AIView::ProcessQuery(hstring const& query)
    {
        co_await winrt::resume_background();

        auto startTime = std::chrono::steady_clock::now();

        co_await winrt::resume_after(std::chrono::milliseconds(500));

        auto elapsed = std::chrono::steady_clock::now() - startTime;
        auto elapsedMs = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();

        auto response = L"AI processing is available when connected to the PDFMind 100M model server. "
                        L"Current query: \"" + std::wstring(query) + L"\"\n\n"
                        L"To enable AI features, ensure the llama.cpp server is running:\n"
                        L"  pdfmind-server.exe --model pdfmind-100m.gguf --port 8080\n\n"
                        L"Processing time: " + std::to_wstring(elapsedMs) + L"ms";

        co_await winrt::resume_foreground([this, response]()
        {
            HideTypingIndicator();
            AppendMessage(L"assistant", response);
        });
    }
}
