#include "pch.h"
#include "Core/CommandManager.h"
#include "Core/CommandManager.g.cpp"

using namespace winrt;

namespace winrt::PDFEditor::implementation
{
    CommandManager::CommandManager()
    {
        m_undoStack.reserve(m_maxDepth);
        m_redoStack.reserve(m_maxDepth);
    }

    void CommandManager::ExecuteCommand(hstring const& name, hstring const& parameters)
    {
        std::lock_guard lock(m_mutex);

        CommandEntry entry;
        entry.name = std::wstring(name);
        entry.parameters = std::wstring(parameters);
        entry.timestamp = std::chrono::steady_clock::now();

        if (m_inMacro)
        {
            m_macroBuffer.push_back(entry);
            return;
        }

        if (ExecuteSingleCommand(entry))
        {
            m_undoStack.push_back(entry);
            m_redoStack.clear();

            while (m_undoStack.size() > m_maxDepth)
            {
                m_undoStack.erase(m_undoStack.begin());
            }
        }
    }

    bool CommandManager::Undo()
    {
        std::lock_guard lock(m_mutex);
        if (m_undoStack.empty()) return false;

        auto entry = m_undoStack.back();
        m_undoStack.pop_back();

        bool success = ReverseCommand(entry);
        if (success)
        {
            m_redoStack.push_back(entry);
        }
        else
        {
            m_undoStack.push_back(entry);
        }

        return success;
    }

    bool CommandManager::Redo()
    {
        std::lock_guard lock(m_mutex);
        if (m_redoStack.empty()) return false;

        auto entry = m_redoStack.back();
        m_redoStack.pop_back();

        bool success = ExecuteSingleCommand(entry);
        if (success)
        {
            m_undoStack.push_back(entry);
        }
        else
        {
            m_redoStack.push_back(entry);
        }

        return success;
    }

    bool CommandManager::CanUndo() const
    {
        return !m_undoStack.empty();
    }

    bool CommandManager::CanRedo() const
    {
        return !m_redoStack.empty();
    }

    uint32_t CommandManager::UndoDepth() const
    {
        return m_maxDepth;
    }

    void CommandManager::UndoDepth(uint32_t value)
    {
        std::lock_guard lock(m_mutex);
        m_maxDepth = std::max(value, 1u);

        while (m_undoStack.size() > m_maxDepth)
        {
            m_undoStack.erase(m_undoStack.begin());
        }
    }

    void CommandManager::Clear()
    {
        std::lock_guard lock(m_mutex);
        m_undoStack.clear();
        m_redoStack.clear();
        m_macroBuffer.clear();
        m_inMacro = false;
    }

    void CommandManager::BeginMacro(hstring const& name)
    {
        std::lock_guard lock(m_mutex);
        m_inMacro = true;
        m_macroBuffer.clear();
    }

    void CommandManager::EndMacro()
    {
        std::lock_guard lock(m_mutex);
        if (!m_inMacro) return;

        m_inMacro = false;

        for (auto const& entry : m_macroBuffer)
        {
            if (ExecuteSingleCommand(entry))
            {
                m_undoStack.push_back(entry);
            }
        }

        m_redoStack.clear();
        m_macroBuffer.clear();
    }

    bool CommandManager::ExecuteSingleCommand(CommandEntry const& entry)
    {
        OutputDebugStringW(L"[CommandManager] Execute: ");
        OutputDebugStringW(entry.name.c_str());
        OutputDebugStringW(L"\n");

        if (entry.name == L"InsertText")
        {
            return true;
        }
        else if (entry.name == L"DeleteText")
        {
            return true;
        }
        else if (entry.name == L"MoveElement")
        {
            return true;
        }
        else if (entry.name == L"InsertPage")
        {
            return true;
        }
        else if (entry.name == L"DeletePage")
        {
            return true;
        }
        else if (entry.name == L"AddAnnotation")
        {
            return true;
        }
        else if (entry.name == L"RemoveAnnotation")
        {
            return true;
        }
        else if (entry.name == L"ModifyAnnotation")
        {
            return true;
        }
        else if (entry.name == L"InsertImage")
        {
            return true;
        }
        else if (entry.name == L"CropPage")
        {
            return true;
        }
        else if (entry.name == L"RotatePage")
        {
            return true;
        }

        return true;
    }

    bool CommandManager::ReverseCommand(CommandEntry const& entry)
    {
        OutputDebugStringW(L"[CommandManager] Undo: ");
        OutputDebugStringW(entry.name.c_str());
        OutputDebugStringW(L"\n");

        if (entry.name == L"InsertText")
        {
            return true;
        }
        else if (entry.name == L"DeleteText")
        {
            return true;
        }
        else if (entry.name == L"InsertPage")
        {
            return true;
        }
        else if (entry.name == L"DeletePage")
        {
            return true;
        }
        else if (entry.name == L"AddAnnotation")
        {
            return true;
        }
        else if (entry.name == L"RemoveAnnotation")
        {
            return true;
        }
        else if (entry.name == L"MoveElement")
        {
            return true;
        }

        return true;
    }
}
