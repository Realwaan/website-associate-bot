"""Convert LaTeX math notation to readable Unicode mathematical symbols."""
import re
from typing import Dict

# Unicode math symbol mappings
LATEX_TO_UNICODE: Dict[str, str] = {
    # Superscripts and subscripts
    r"\^2": "²",
    r"\^3": "³",
    r"\^4": "⁴",
    r"\^5": "⁵",
    r"\^6": "⁶",
    r"\^7": "⁷",
    r"\^8": "⁸",
    r"\^9": "⁹",
    r"\^0": "⁰",
    r"\^1": "¹",
    
    # Greek letters
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\delta": "δ",
    r"\epsilon": "ε",
    r"\zeta": "ζ",
    r"\eta": "η",
    r"\theta": "θ",
    r"\iota": "ι",
    r"\kappa": "κ",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\nu": "ν",
    r"\xi": "ξ",
    r"\pi": "π",
    r"\rho": "ρ",
    r"\sigma": "σ",
    r"\tau": "τ",
    r"\upsilon": "υ",
    r"\phi": "φ",
    r"\chi": "χ",
    r"\psi": "ψ",
    r"\omega": "ω",
    
    # Capital Greek
    r"\Pi": "Π",
    r"\Sigma": "Σ",
    r"\Delta": "Δ",
    r"\Lambda": "Λ",
    r"\Omega": "Ω",
    
    # Math operators and symbols
    r"\infty": "∞",
    r"\pm": "±",
    r"\times": "×",
    r"\div": "÷",
    r"\cdot": "·",
    r"\le": "≤",
    r"\leq": "≤",
    r"\ge": "≥",
    r"\geq": "≥",
    r"\neq": "≠",
    r"\approx": "≈",
    r"\equiv": "≡",
    r"\sim": "~",
    r"\propto": "∝",
    r"\in": "∈",
    r"\notin": "∉",
    r"\subset": "⊂",
    r"\supset": "⊃",
    r"\subseteq": "⊆",
    r"\supseteq": "⊇",
    r"\cup": "∪",
    r"\cap": "∩",
    r"\forall": "∀",
    r"\exists": "∃",
    r"\emptyset": "∅",
    r"\nabla": "∇",
    r"\partial": "∂",
    r"\sum": "Σ",
    r"\int": "∫",
    r"\sqrt": "√",
    r"\leftarrow": "←",
    r"\rightarrow": "→",
    r"\leftrightarrow": "↔",
    r"\implies": "⟹",
    r"\iff": "⟺",
    
    # Fractions and special
    r"\frac{1}{2}": "½",
    r"\frac{1}{3}": "⅓",
    r"\frac{2}{3}": "⅔",
    r"\frac{1}{4}": "¼",
    r"\frac{3}{4}": "¾",
}


def convert_latex_equation(latex_str: str) -> str:
    """
    Convert LaTeX math notation to Unicode mathematical symbols.
    
    Parameters
    ----------
    latex_str : str
        LaTeX equation string
        
    Returns
    -------
    str
        Converted equation with Unicode symbols
    """
    result = latex_str
    
    # Remove common LaTeX formatting that clutters display
    # Remove \left and \right
    result = result.replace(r"\left", "").replace(r"\right", "")
    
    # Convert fractions in the format \frac{a}{b}
    # First try simple numeric fractions
    for latex_frac, unicode_frac in LATEX_TO_UNICODE.items():
        if "frac" in latex_frac:
            result = result.replace(latex_frac, unicode_frac)
    
    # Remove extra whitespace inside braces for cleaner display
    result = re.sub(r'\{\s*', '{', result)
    result = re.sub(r'\s*\}', '}', result)
    
    # Convert individual LaTeX commands to Unicode
    for latex_cmd, unicode_symbol in LATEX_TO_UNICODE.items():
        result = result.replace(latex_cmd, unicode_symbol)
    
    # Clean up brackets notation: {expression} -> (expression)
    # But keep necessary braces for clarity
    result = re.sub(r'\{\s*(\d+)\s*\}', r'(\1)', result)
    
    # Convert common power patterns like (x)^2 to x²
    result = re.sub(r'\(([a-zA-Z])\)\^(\d)', lambda m: f"({m.group(1)})" + chr(0x00B2 + int(m.group(2)) - 2) if int(m.group(2)) in [2,3] else m.group(0), result)
    
    # Format integrals more nicely
    result = re.sub(r'\\int_\{([^}]+)\}\^\{([^}]+)\}', r'∫_{1}^{2} ', result)
    
    return result


def format_equation_display(text: str) -> str:
    """
    Format text with equations for Discord display.
    Converts LaTeX to Unicode and improves readability.
    
    Parameters
    ----------
    text : str
        Text containing LaTeX equations
        
    Returns
    -------
    str
        Formatted text with Unicode math symbols
    """
    # Extract and convert display equations ($$...$$)
    def convert_display_eq(match):
        latex_eq = match.group(1).strip()
        unicode_eq = convert_latex_equation(latex_eq)
        # Add newlines around display equations for better readability
        return f"\n**{unicode_eq}**\n"
    
    result = re.sub(r'\$\$(.*?)\$\$', convert_display_eq, text, flags=re.DOTALL)
    
    # Extract and convert inline equations ($...$)
    def convert_inline_eq(match):
        latex_eq = match.group(1).strip()
        unicode_eq = convert_latex_equation(latex_eq)
        return unicode_eq
    
    result = re.sub(r'(?<!\$)\$(?!\$)(.*?)\$(?!\$)', convert_inline_eq, result)
    
    return result
