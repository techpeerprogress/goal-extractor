# Prompts Directory

This directory contains prompt templates stored as markdown files. These prompts are automatically loaded by `prompts.py` when the module is imported.

## How It Works

1. Each prompt is stored as a `.md` file in this directory
2. The filename is converted to a constant name:
   - `goal_extraction.md` → `GOAL_EXTRACTION`
   - `marketing_activity_extraction.md` → `MARKETING_ACTIVITY_EXTRACTION`
   - `my-new-prompt.md` → `MY_NEW_PROMPT`
3. Prompts are loaded automatically when `import prompts` is called
4. If a markdown file doesn't exist, the system falls back to hardcoded prompts in `prompts.py`

## Creating a New Prompt

1. Create a new `.md` file in this directory (e.g., `my_prompt.md`)
2. Add your prompt content to the file
3. It will be accessible as `prompts.MY_PROMPT` in your Python code

## Adding Template Variables

Prompts can include template variables using `{variable_name}` syntax:
- `{transcript}` - will be replaced with the transcript text
- `{commitments}` - will be replaced with commitments data
- etc.

These can be formatted using `.format()` as usual:
```python
prompt_text = prompts.MY_PROMPT.format(variable_name="value")
```

## Current Prompts

- `goal_extraction.md` → `GOAL_EXTRACTION`
- (Add more as you create them)

## Benefits

✅ **Better editing**: Markdown files are easier to edit and version control  
✅ **Syntax highlighting**: Most editors support markdown syntax highlighting  
✅ **Readability**: Easier to read and maintain than Python strings  
✅ **Version control**: Track prompt changes in git history  
✅ **Sharing**: Easy to share prompts with team members

