# AI Meme Generator

A web app created using Flask that generates memes by using OpenAI for the text and prompt generation, plus optional ClipDrop / StabilityAI image generation.

## What is included in the project:

- `app.py`: Flask application entrypoint for running the web server.
- `AIMemeGenerator.py`: meme generation logic, including prompt creation and image generation.
- `templates/`: HTML templates for the home page and result display.
- `static/`: site CSS.
- `assets/api_keys_empty.ini`: placeholder API key config that is safe to keep in the repo.
- `api_keys.ini`: local API key file for your own credentials.

## Setup

1. Create a local Python virtual environment:

```bash
cd /Users/shrutituteja/Desktop/Full-Stack-AI-Meme-Generator-main
python3 -m venv .venv
```

2. Activate the virtual environment:

```bash
source .venv/bin/activate
```

3. Install the required packages:

```bash
pip install --upgrade pip setuptools wheel
pip install --prefer-binary -r Requirements.txt
```

4. Configure your API keys in `api_keys.ini`.

### `api_keys.ini` example:

```ini
[Keys]
OpenAI = "Enter your API"
ClipDrop = "Enter your API"
StabilityAI = "Enter your API"
```

Replace the placeholder values with your actual API keys.

## Running the app

Start the server with:

```bash
python app.py
```

Then open the server:

```
http://127.0.0.1:5000
```

## Recommended files to commit to GitHub

- `AIMemeGenerator.py`
- `app.py`
- `Requirements.txt`
- `templates/`
- `static/`
- `assets/api_keys_empty.ini`
- `settings.ini` (if it contains only non-sensitive default settings)
- `README.md`
- `.gitignore`

## Files to keep private or avoid committing

- `api_keys.ini` (contains your real API keys)
- `.venv/` or `myenv/` (local Python environments)
- `__pycache__/`
- `Outputs/` (generated files)
- any local log files or system-specific files

## Notes

- The project uses `api_keys.ini` for your API credentials.
- `assets/api_keys_empty.ini` is a safe default file for repository inclusion.
- `.gitignore` has been updated to ignore local virtual environments and `api_keys.ini`.
