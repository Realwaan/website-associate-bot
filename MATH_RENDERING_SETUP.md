# Math Equation Rendering Setup

## Overview
The bot now converts LaTeX math equations to beautiful PNG images that display properly in Discord.

## Prerequisites

### 1. **LaTeX Installation** (Required)
Needed to compile `.tex` → `.pdf`

**Windows:**
```bash
choco install miktex
# or
scoop install miktex
```

**macOS:**
```bash
brew install mactex
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install texlive-latex-base texlive-latex-extra
```

### 2. **ImageMagick** (Required)
Needed to convert `.pdf` → `.png`

**Windows:**
```bash
choco install imagemagick
# or
scoop install imagemagick
```

**macOS:**
```bash
brew install imagemagick
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install imagemagick
```

### 3. **Python Dependencies**
```bash
pip install -r requirements.txt
```

## How It Works

### Input
```
For rotation about the x-axis:$$V = \pi \int_{a}^{b} \left[ (R(x))^2 - (r(x))^2 \right] dx$$
```

### Processing
1. **Extract equations** using regex (LaTeX patterns)
2. **Render to PDF** using `pdflatex`
3. **Convert to PNG** using ImageMagick
4. **Embed images** in Discord message
5. **Replace text** with `[Equation N]` placeholders

### Output
Discord embed shows:
- Description with equation placeholders
- Attached PNG images of rendered equations
- Footer noting number of equations rendered

## Features

✅ **Automatic Detection** - Finds all `$$...$$` (display) and `$...$` (inline) math
✅ **Beautiful Rendering** - Professional mathematical notation
✅ **Fast Fallback** - If rendering fails, shows original LaTeX
✅ **Multiple Equations** - Handles many equations in one response
✅ **Quality Control** - 150 DPI default (adjustable in code)

## Configuration

In `math_renderer.py`, adjust rendering quality:

```python
# Higher DPI = better quality but larger file size
png_bytes = render_latex_to_png(eq_code, dpi=150)  # Default
png_bytes = render_latex_to_png(eq_code, dpi=300)  # High quality
png_bytes = render_latex_to_png(eq_code, dpi=100)  # Small file
```

## Troubleshooting

### "LaTeX not installed" warning
- Ensure `pdflatex` is in your system PATH
- Verify installation: `pdflatex --version`

### "ImageMagick not installed" warning  
- Ensure `convert` command is available
- Verify installation: `convert --version`
- May need to enable ImageMagick in config on some systems

### Equations not rendering
- Check logs: `logger.debug()` messages
- Verify LaTeX syntax is correct
- Try rendering simpler equations first

### File size too large
- Reduce DPI (100 instead of 150)
- Complex equations will always be larger

## Example Usage

User query:
```
/ask-ai What is the Pythagorean theorem?
```

Bot response shows:
```
The Pythagorean theorem states that in a right triangle:

[Equation 1]

Where a and b are the legs and c is the hypotenuse.
```

Plus attached image of: `a² + b² = c²`

## Performance Notes

- **First render**: ~1-2 seconds (LaTeX compilation)
- **Subsequent renders**: ~0.5-1 second (ImageMagick conversion)
- **File size**: 5-50 KB per equation depending on complexity
- **Discord upload limit**: 25 MB per message (not a concern)

## Fallback Behavior

If math rendering is unavailable:
1. LaTeX not installed → Shows original `$$...$$ text
2. ImageMagick not installed → Shows original `$$...$$ text
3. Rendering timeout → Shows original `$$...$$ text
4. Bot continues normally (graceful degradation)

## Future Improvements

- [ ] Cache rendered equations to avoid re-rendering
- [ ] Support TikZ diagrams (complex graphics)
- [ ] Add color support for dark/light Discord themes
- [ ] Async rendering pool for faster processing
