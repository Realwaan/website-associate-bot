import unittest
from math_renderer import (
    extract_latex_equations,
    count_equations,
    format_for_discord_display,
)
from main import _strip_latex_equations, _format_math_content


class TestMathFallback(unittest.TestCase):
    def test_extract_equations(self):
        """Verify extraction of display and inline equations."""
        text = "Here is some text: $$V = \\pi r^2 h$$ and inline $E = mc^2$ formulas."
        equations = extract_latex_equations(text)
        
        self.assertEqual(len(equations), 2)
        # First equation (display)
        self.assertEqual(equations[0][1], 'display')
        self.assertEqual(equations[0][2], 'V = \\pi r^2 h')
        
        # Second equation (inline)
        self.assertEqual(equations[1][1], 'inline')
        self.assertEqual(equations[1][2], 'E = mc^2')

    def test_count_equations(self):
        """Verify equation counter matches expected amounts."""
        text = "$$eq1$$ and $eq2$ and $$eq3$$"
        counts = count_equations(text)
        self.assertEqual(counts['display'], 2)
        self.assertEqual(counts['inline'], 1)

    def test_strip_equations(self):
        """Verify _strip_latex_equations removes equations for cleaner embeds."""
        text = "Start $$V = \\pi r^2 h$$ middle $E = mc^2$ end."
        stripped = _strip_latex_equations(text)
        self.assertEqual(stripped, "Start  middle  end.")

    def test_format_math_content_display(self):
        """Verify _format_math_content converts display equations to latex code blocks."""
        text = "Equation: $$x + y = z$$"
        formatted = _format_math_content(text)
        self.assertIn("```latex\nx + y = z\n```", formatted)

    def test_fallback_behavior_math_preservation(self):
        """Verify that when rendering fails, original equations are preserved in formatted text."""
        # Simulated fallback flow
        answer = "Solve: $$2x = 4$$ therefore $x = 2$."
        
        # If rendering fails, we should NOT strip equations, but call _format_math_content(answer)
        formatted_fallback = _format_math_content(answer)
        self.assertIn("```latex\n2x = 4\n```", formatted_fallback)
        self.assertIn("$x = 2$", formatted_fallback)
        
        # If rendering succeeds, we strip them and display placeholders
        display_text = _strip_latex_equations(answer)
        formatted_success = _format_math_content(display_text)
        self.assertNotIn("2x = 4", formatted_success)
        self.assertNotIn("x = 2", formatted_success)


if __name__ == '__main__':
    unittest.main()
