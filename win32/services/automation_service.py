import os
import json


class AutomationService:
    def __init__(self, editor):
        self.editor = editor
        self._actions = {}
        self._actions_dir = os.path.join(os.path.dirname(__file__), "..", "data", "actions")
        os.makedirs(self._actions_dir, exist_ok=True)

    def create_action(self, name, steps_list):
        """Create a new action with a list of step dicts."""
        try:
            self._actions[name] = {
                "name": name,
                "steps": steps_list
            }
        except Exception as e:
            raise RuntimeError(f"Cannot create action: {e}")

    def save_action(self, name, filepath):
        """Save an action to a JSON file."""
        try:
            if name not in self._actions:
                raise ValueError(f"Action '{name}' not found")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._actions[name], f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Cannot save action: {e}")

    def load_action(self, filepath):
        """Load an action from a JSON file. Returns the action dict."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                action = json.load(f)
            name = action.get("name", os.path.basename(filepath))
            self._actions[name] = action
            return action
        except Exception as e:
            raise RuntimeError(f"Cannot load action: {e}")

    def run_action(self, action_name):
        """Execute all steps in the named action."""
        try:
            if action_name not in self._actions:
                raise ValueError(f"Action '{action_name}' not found")
            action = self._actions[action_name]
            steps = action.get("steps", [])
            for step in steps:
                self._execute_step(step)
            self.editor.canvas_manager.update_preview()
        except Exception as e:
            raise RuntimeError(f"Cannot run action: {e}")

    def list_actions(self):
        """Return list of all action names."""
        return list(self._actions.keys())

    def delete_action(self, name):
        """Delete an action by name."""
        try:
            if name in self._actions:
                del self._actions[name]
        except Exception as e:
            raise RuntimeError(f"Cannot delete action: {e}")

    def _execute_step(self, step):
        """Execute a single action step."""
        action_type = step.get("type", "")
        params = {k: v for k, v in step.items() if k != "type"}
        try:
            if action_type == "set_watermark":
                text = params.get("text", "WATERMARK")
                page = params.get("page", -1)
                self.editor.watermark_service.add_text_watermark(
                    text=text, page=page,
                    size=params.get("size", 60),
                    color=params.get("color", "#888888"),
                    opacity=params.get("opacity", 0.3),
                    rotation=params.get("rotation", 45)
                )
            elif action_type == "add_header_footer":
                text = params.get("text", "{page} / {total}")
                position = params.get("position", "footer-center")
                self.editor.header_footer_service.add_header_footer(
                    text=text, position=position,
                    size=params.get("size", 10),
                    color=params.get("color", "#666666")
                )
            elif action_type == "add_stamp":
                text = params.get("text", "APPROVED")
                self.editor.stamp_elements = getattr(self.editor, "stamp_elements", [])
            elif action_type == "password_protect":
                password = params.get("password", "")
                if password:
                    self.editor.security_service.encrypt_pdf(
                        password, params.get("owner_password", "")
                    )
            elif action_type == "compress":
                input_path = params.get("input_path", "")
                output_path = params.get("output_path", "")
                level = params.get("level", "medium")
                if input_path and output_path:
                    self.editor.compress_service.compress(input_path, output_path, level)
            elif action_type == "export_images":
                output_dir = params.get("output_dir", "")
                if output_dir:
                    self.editor.export_service.export_as_images(output_dir)
        except Exception as e:
            pass
