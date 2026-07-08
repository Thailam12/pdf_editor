# undo_redo.py - Undo/Redo management system
from copy import deepcopy

class UndoRedoManager:
    def __init__(self, max_history=50):
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = max_history
    
    def save_state(self, state):
        """Save current state to undo stack"""
        self.undo_stack.append(deepcopy(state))
        self.redo_stack.clear()  # Clear redo stack when new action is taken
        
        # Limit history size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
    
    def undo(self, current_state):
        """Get previous state"""
        if not self.can_undo():
            return current_state
        
        self.redo_stack.append(deepcopy(current_state))
        return self.undo_stack.pop()
    
    def redo(self, current_state):
        """Get next state"""
        if not self.can_redo():
            return current_state
        
        self.undo_stack.append(deepcopy(current_state))
        return self.redo_stack.pop()
    
    def can_undo(self):
        return len(self.undo_stack) > 0
    
    def can_redo(self):
        return len(self.redo_stack) > 0
    
    def clear(self):
        """Clear all history"""
        self.undo_stack.clear()
        self.redo_stack.clear()
