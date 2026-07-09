from models.elements import elements_to_json_list, elements_from_json_list


class UndoRedoManager:
    def __init__(self, max_history=50):
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = max_history

    def save_state(self, elements):
        json_data = elements_to_json_list(elements)
        self.undo_stack.append(json_data)
        self.redo_stack.clear()
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)

    def undo(self, current_elements):
        if not self.can_undo():
            return list(current_elements)
        self.redo_stack.append(elements_to_json_list(current_elements))
        json_data = self.undo_stack.pop()
        return elements_from_json_list(json_data)

    def redo(self, current_elements):
        if not self.can_redo():
            return list(current_elements)
        self.undo_stack.append(elements_to_json_list(current_elements))
        json_data = self.redo_stack.pop()
        return elements_from_json_list(json_data)

    def can_undo(self):
        return len(self.undo_stack) > 0

    def can_redo(self):
        return len(self.redo_stack) > 0

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
