#pragma once

#include "Core/CommandManager.g.h"

namespace winrt::PDFEditor::implementation
{
    struct CommandEntry
    {
        std::wstring name;
        std::wstring parameters;
        std::chrono::steady_clock::time_point timestamp;
    };

    struct CommandManager : CommandManagerT<CommandManager>
    {
        CommandManager();

        void ExecuteCommand(hstring const& name, hstring const& parameters);
        bool Undo();
        bool Redo();

        bool CanUndo() const;
        bool CanRedo() const;
        uint32_t UndoDepth() const;
        void UndoDepth(uint32_t value);

        void Clear();
        void BeginMacro(hstring const& name);
        void EndMacro();

    private:
        bool ExecuteSingleCommand(CommandEntry const& entry);
        bool ReverseCommand(CommandEntry const& entry);

        std::vector<CommandEntry> m_undoStack;
        std::vector<CommandEntry> m_redoStack;
        uint32_t m_maxDepth{ 100 };
        bool m_inMacro{ false };
        std::vector<CommandEntry> m_macroBuffer;

        std::mutex m_mutex;
    };
}
