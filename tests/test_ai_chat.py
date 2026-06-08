import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import discord
from ai_client import NvidiaAIClient, AIClientError
from main import on_message


class TestAIChatThread(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = NvidiaAIClient()

    @patch('ai_client.OpenAI')
    def test_chat_client_single_prompt(self, mock_openai):
        """Verify that single string prompts construct basic message payloads."""
        mock_completions = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Answer content"
        mock_response.choices = [mock_choice]
        mock_completions.create.return_value = mock_response
        mock_openai.return_value.chat.completions = mock_completions

        with patch.dict('os.environ', {'AI_ANSWER_API_KEY': 'nvapi-key', 'AI_ANSWER_MODEL': 'meta/llama3'}):
            res = self.client.chat("Hello AI")
            self.assertEqual(res, "Answer content")
            
            # Verify system + user prompts
            call_kwargs = mock_completions.create.call_args[1]
            messages = call_kwargs['messages']
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]['role'], 'system')
            self.assertEqual(messages[1]['role'], 'user')
            self.assertEqual(messages[1]['content'], 'Hello AI')

    @patch('ai_client.OpenAI')
    def test_chat_client_history_list(self, mock_openai):
        """Verify that message lists are correctly forwarded as conversation history."""
        mock_completions = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Continuation content"
        mock_response.choices = [mock_choice]
        mock_completions.create.return_value = mock_response
        mock_openai.return_value.chat.completions = mock_completions

        history = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"}
        ]

        with patch.dict('os.environ', {'AI_ANSWER_API_KEY': 'nvapi-key', 'AI_ANSWER_MODEL': 'meta/llama3'}):
            res = self.client.chat(history)
            self.assertEqual(res, "Continuation content")
            
            # Verify system + history payload
            call_kwargs = mock_completions.create.call_args[1]
            messages = call_kwargs['messages']
            self.assertEqual(len(messages), 4)
            self.assertEqual(messages[0]['role'], 'system')
            self.assertEqual(messages[1]['role'], 'user')
            self.assertEqual(messages[1]['content'], 'Question 1')
            self.assertEqual(messages[2]['role'], 'assistant')
            self.assertEqual(messages[2]['content'], 'Answer 1')
            self.assertEqual(messages[3]['role'], 'user')
            self.assertEqual(messages[3]['content'], 'Question 2')

    @patch('main.async_has_role')
    @patch('main.ai_client')
    @patch('main.bot')
    @patch('main.has_latex')
    async def test_on_message_ai_chat_thread(self, mock_has_latex, mock_bot, mock_ai_client, mock_async_has_role):
        """Verify that messages in AI-Chat threads trigger history assembly and LLM calls."""
        mock_async_has_role.return_value = True
        mock_ai_client.chat = MagicMock(return_value="AI Reply content")
        mock_bot.user.id = 12345
        mock_has_latex.return_value = False

        # Mock message channel as Thread
        mock_thread = MagicMock(spec=discord.Thread)
        mock_thread.name = "💬 AI-Chat: physics-discussion"
        
        # Mock typing context manager
        mock_typing = AsyncMock()
        mock_thread.typing.return_value = mock_typing

        # Mock thread history
        mock_msg_1 = MagicMock(spec=discord.Message)
        mock_msg_1.content = "Question 1"
        mock_msg_1.author.id = 99999
        mock_msg_1.created_at = 1

        mock_msg_2 = MagicMock(spec=discord.Message)
        mock_msg_2.content = "Answer 1"
        mock_msg_2.author.id = 12345
        mock_msg_2.created_at = 2

        mock_msg_3 = MagicMock(spec=discord.Message)
        mock_msg_3.content = "Question 2"
        mock_msg_3.author.id = 99999
        mock_msg_3.created_at = 3

        async def mock_history(limit):
            yield mock_msg_3
            yield mock_msg_2
            yield mock_msg_1

        mock_thread.history = mock_history
        mock_thread.send = AsyncMock()

        # Mock the trigger message
        mock_message = MagicMock(spec=discord.Message)
        mock_message.author.id = 99999
        mock_message.channel = mock_thread
        mock_message.content = "Question 2"
        mock_message.mentions = []

        # Run on_message
        await on_message(mock_message)

        # Check typing was activated
        mock_thread.typing.assert_called_once()
        
        # Check LLM was called with assembled history list
        mock_ai_client.chat.assert_called_once()
        call_args = mock_ai_client.chat.call_args[0][0]
        self.assertEqual(len(call_args), 3)
        self.assertEqual(call_args[0]['role'], 'user')
        self.assertEqual(call_args[0]['content'], 'Question 1')
        self.assertEqual(call_args[1]['role'], 'assistant')
        self.assertEqual(call_args[1]['content'], 'Answer 1')
        self.assertEqual(call_args[2]['role'], 'user')
        self.assertEqual(call_args[2]['content'], 'Question 2')

        # Check send was called with AI output
        mock_thread.send.assert_called_once_with("AI Reply content")

    @patch('main.async_has_role')
    @patch('main.ai_client')
    @patch('main.bot')
    @patch('main.has_latex')
    @patch('main.render_equations_to_single_png')
    async def test_on_message_ai_chat_thread_with_math(self, mock_render, mock_has_latex, mock_bot, mock_ai_client, mock_async_has_role):
        """Verify that math content in thread messages invokes render_equations_to_single_png."""
        mock_async_has_role.return_value = True
        mock_ai_client.chat = MagicMock(return_value="AI Reply with equation: $$V = \\pi r^2 h$$")
        mock_bot.user.id = 12345
        mock_has_latex.return_value = True
        mock_render.return_value = b"fake_png_bytes"

        # Mock message channel as Thread
        mock_thread = MagicMock(spec=discord.Thread)
        mock_thread.name = "💬 AI-Chat: physics-discussion"
        
        # Mock typing context manager
        mock_typing = AsyncMock()
        mock_thread.typing.return_value = mock_typing

        # Mock thread history
        mock_msg_1 = MagicMock(spec=discord.Message)
        mock_msg_1.content = "Question 1"
        mock_msg_1.author.id = 99999
        mock_msg_1.created_at = 1

        async def mock_history(limit):
            yield mock_msg_1

        mock_thread.history = mock_history
        mock_thread.send = AsyncMock()

        # Mock the trigger message
        mock_message = MagicMock(spec=discord.Message)
        mock_message.author.id = 99999
        mock_message.channel = mock_thread
        mock_message.content = "Question 1"
        mock_message.mentions = []

        # Run on_message
        await on_message(mock_message)

        # Check that math rendering was called
        mock_render.assert_called_once_with("AI Reply with equation: $$V = \\pi r^2 h$$")
        
        # Check that thread.send was called with an attachment embed
        mock_thread.send.assert_called_once()
        call_kwargs = mock_thread.send.call_args[1]
        self.assertIn("embed", call_kwargs)
        self.assertIn("file", call_kwargs)


if __name__ == '__main__':
    unittest.main()
