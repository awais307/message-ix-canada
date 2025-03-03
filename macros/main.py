import os

def define_env(env):
    """Hook for MkDocs Macros plugin."""
    @env.macro
    def read_file(filepath):
        """Read file contents and return as string."""
        full_path = os.path.join("docs", filepath)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"Error: {filepath} not found"
