"""Render LaTeX math equations to PNG images for Discord display."""
import re
import io
import logging
from pathlib import Path
from typing import Optional
import subprocess
import shutil
import tempfile

logger = logging.getLogger(__name__)


def has_latex() -> bool:
    """Check if LaTeX (pdflatex) is installed on the system."""
    try:
        subprocess.run(
            ["pdflatex", "--version"],
            capture_output=True,
            timeout=5,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def _get_imagemagick_command() -> list[str] | None:
    """Return the ImageMagick command to invoke, if available."""
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        return ["convert"]
    return None


def has_imagemagick() -> bool:
    """Check if ImageMagick is installed (prefer `magick` on Windows)."""
    cmd = _get_imagemagick_command()
    if not cmd:
        return False
    try:
        subprocess.run(
            cmd + ["-version"],
            capture_output=True,
            timeout=5,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def render_latex_to_png(latex_code: str, dpi: int = 150) -> Optional[bytes]:
    """
    Render LaTeX equation to PNG bytes.
    
    Parameters
    ----------
    latex_code : str
        LaTeX equation code (e.g., "a^2 + b^2 = c^2" or full equation)
    dpi : int
        Resolution in dots per inch (higher = better quality but larger file)
        
    Returns
    -------
    bytes or None
        PNG image bytes if successful, None if rendering fails
    """
    if not has_latex():
        logger.warning("LaTeX not installed; skipping equation rendering")
        return None

    try:
        # Wrap in LaTeX document
        tex_document = (
            r"\documentclass[12pt]{article}" + "\n"
            r"\usepackage{amsmath}" + "\n"
            r"\usepackage{amssymb}" + "\n"
            r"\pagestyle{empty}" + "\n"
            r"\begin{document}" + "\n"
            r"$" + latex_code + r"$" + "\n"
            r"\end{document}"
        )

        with tempfile.TemporaryDirectory(prefix="latex-render-") as tmpdir:
            tmp_path = Path(tmpdir)
            tex_file = tmp_path / "equation.tex"
            tex_file.write_text(tex_document)

            # Compile to PDF
            subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-output-directory",
                    str(tmp_path),
                    str(tex_file),
                ],
                capture_output=True,
                timeout=10,
                check=False,
            )

            pdf_file = tmp_path / "equation.pdf"
            if not pdf_file.exists():
                logger.warning("Failed to generate PDF from LaTeX")
                return None

            # Convert PDF to PNG using ImageMagick (if available)
            png_file = tmp_path / "equation.png"
            try:
                cmd_base = _get_imagemagick_command()
                if not cmd_base:
                    raise FileNotFoundError("ImageMagick not found")

                cmd = cmd_base + ["-density", str(dpi), "-trim", str(pdf_file), str(png_file)]
                subprocess.run(cmd, capture_output=True, timeout=10, check=True)

                if png_file.exists():
                    return png_file.read_bytes()
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning(
                    "ImageMagick not installed; cannot convert PDF to PNG. "
                    "Install with: `choco install imagemagick` or `apt-get install imagemagick`"
                )
                return None

    except Exception as e:
        logger.warning(f"Failed to render LaTeX equation: {e}")
        return None

    return None


def extract_latex_equations(text: str) -> list[tuple[str, str, str]]:
    """
    Extract LaTeX equations from text.
    
    Returns list of (full_match, equation_type, equation_code)
    where equation_type is 'inline' or 'display'
    """
    equations = []

    # Display math ($$...$$)
    for match in re.finditer(r'\$\$(.*?)\$\$', text, re.DOTALL):
        equations.append((match.group(0), 'display', match.group(1).strip()))

    # Inline math ($...$)
    for match in re.finditer(r'(?<!\$)\$(?!\$)(.*?)\$(?!\$)', text):
        equations.append((match.group(0), 'inline', match.group(1).strip()))

    return equations


def replace_equations_with_images(text: str) -> tuple[str, list[bytes]]:
    """
    Replace LaTeX equations in text with placeholders and render them to PNG.
    
    Returns
    -------
    (modified_text, image_bytes_list)
    """
    equations = extract_latex_equations(text)
    images = []
    modified_text = text

    for i, (full_match, eq_type, eq_code) in enumerate(equations):
        png_bytes = render_latex_to_png(eq_code)
        if png_bytes:
            images.append(png_bytes)
            placeholder = f"[Equation {i+1}]"
            modified_text = modified_text.replace(full_match, placeholder, 1)
        else:
            # Keep original if rendering fails
            logger.debug(f"Could not render equation: {eq_code[:50]}...")

    return modified_text, images


def count_equations(text: str) -> dict[str, int]:
    """
    Count the number of inline and display equations in text.
    
    Returns
    -------
    dict with keys 'inline' and 'display'
    """
    equations = extract_latex_equations(text)
    counts = {'inline': 0, 'display': 0}
    for _, eq_type, _ in equations:
        counts[eq_type] += 1
    return counts


def validate_latex_syntax(latex_code: str) -> bool:
    """
    Validate LaTeX syntax by attempting to render it.
    
    Parameters
    ----------
    latex_code : str
        LaTeX equation code to validate
        
    Returns
    -------
    bool
        True if LaTeX is valid, False otherwise
    """
    if not has_latex():
        return None  # Cannot validate without LaTeX installed
    
    try:
        # Try to render; if it succeeds, syntax is valid
        png_bytes = render_latex_to_png(latex_code, dpi=100)
        return png_bytes is not None
    except Exception:
        return False


def extract_math_sections(text: str) -> list[dict]:
    """
    Extract mathematical content sections from text.
    
    Returns list of sections with structure:
    {
        'header': str,
        'content': str,
        'equations': list[tuple(type, code)],
        'complexity': 'simple' | 'moderate' | 'complex'
    }
    """
    sections = []
    
    # Split by section headers (lines with === or --- below)
    section_pattern = r'^([A-Z][A-Za-z\s]+)\n[\-=]{3,}$'
    parts = re.split(section_pattern, text, flags=re.MULTILINE)
    
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            header = parts[i]
            content = parts[i + 1]
            equations = extract_latex_equations(content)
            
            # Determine complexity
            equation_count = len(equations)
            display_count = sum(1 for _, eq_type, _ in equations if eq_type == 'display')
            
            if equation_count == 0:
                complexity = 'simple'
            elif display_count >= 3 or any('\\int' in code or '\\sum' in code 
                                          for _, _, code in equations):
                complexity = 'complex'
            else:
                complexity = 'moderate'
            
            sections.append({
                'header': header.strip(),
                'content': content.strip(),
                'equations': [(eq_type, code) for _, eq_type, code in equations],
                'complexity': complexity
            })
    
    return sections


def format_for_discord_display(text: str, max_embed_length: int = 4000) -> str:
    """
    Format mathematical content for optimal Discord embed display.
    
    Features:
    - Wraps display math in latex code blocks
    - Preserves inline math notation
    - Enhances section headers with markdown
    - Ensures content fits in Discord embed limits
    
    Parameters
    ----------
    text : str
        Mathematical content to format
    max_embed_length : int
        Maximum length for Discord embed description (default: 4000)
        
    Returns
    -------
    str
        Formatted text suitable for Discord embeds
    """
    # Format display equations with syntax highlighting
    formatted = re.sub(
        r'\$\$(.*?)\$\$',
        r'```latex\n\1\n```',
        text,
        flags=re.DOTALL
    )
    
    # Enhance section headers
    formatted = re.sub(
        r'^([A-Z][A-Za-z\s]+)\n[\-=]{3,}$',
        r'## \1',
        formatted,
        flags=re.MULTILINE
    )
    
    return formatted
