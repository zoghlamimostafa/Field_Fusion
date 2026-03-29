"""
Interactive Coach Chat Interface
=================================

Gradio-based chat interface for LLM Coach Assistant
Allows coaches to have natural conversations about match analysis
"""

import gradio as gr
import json
import os
from llm_coach_assistant import LLMCoachAssistant


class CoachChatInterface:
    """Interactive chat interface for coaches"""

    def __init__(self):
        self.assistant_en = LLMCoachAssistant(language='en')
        self.assistant_ar = LLMCoachAssistant(language='ar')
        self.assistant_fr = LLMCoachAssistant(language='fr')

        self.current_session = None
        self.analytics_data = None

    def load_match_data(self, analytics_path: str):
        """Load match analytics from JSON"""
        try:
            with open(analytics_path, 'r') as f:
                self.analytics_data = json.load(f)
            return "✅ Match data loaded successfully!"
        except Exception as e:
            return f"❌ Error loading match data: {e}"

    def start_chat(self, match_name: str, language: str):
        """Start a new chat session"""
        assistant = self._get_assistant(language)

        if self.analytics_data is None:
            return "❌ Please load match data first!", []

        self.current_session = assistant.start_session(match_name, self.analytics_data)

        welcome_messages = {
            'en': "Hello! I'm your AI coach assistant. I've analyzed the match data. What would you like to know?",
            'ar': "مرحباً! أنا مساعد المدرب بالذكاء الاصطناعي. لقد قمت بتحليل بيانات المباراة. ما الذي تريد معرفته؟",
            'fr': "Bonjour! Je suis votre assistant d'entraîneur IA. J'ai analysé les données du match. Que voulez-vous savoir?"
        }

        return welcome_messages.get(language, welcome_messages['en']), []

    def _get_assistant(self, language: str):
        """Get assistant for language"""
        if language == 'ar':
            return self.assistant_ar
        elif language == 'fr':
            return self.assistant_fr
        else:
            return self.assistant_en

    def chat(self, message: str, history: list, language: str):
        """Process chat message"""
        assistant = self._get_assistant(language)

        if not self.current_session:
            return history, "Please start a session first!"

        # Get response
        response = assistant.ask_question(message, self.current_session)

        # Update history
        history.append((message, response))

        return history, ""

    def generate_narrative(self, language: str):
        """Generate match narrative"""
        assistant = self._get_assistant(language)

        if self.analytics_data is None:
            return "❌ Please load match data first!"

        narrative = assistant.generate_match_narrative(self.analytics_data)

        return narrative

    def generate_recommendations(self, language: str):
        """Generate tactical recommendations"""
        assistant = self._get_assistant(language)

        if self.analytics_data is None:
            return "❌ Please load match data first!"

        recommendations = assistant.generate_tactical_recommendations(self.analytics_data)

        return "\n".join(recommendations)


def create_interface():
    """Create Gradio interface"""

    chat_interface = CoachChatInterface()

    with gr.Blocks(title="🤖 AI Coach Assistant", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🤖 AI Coach Assistant")
        gr.Markdown("### Powered by Claude Sonnet 4.5 - Natural Language Match Analysis")

        with gr.Tab("💬 Interactive Chat"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Setup")

                    analytics_file = gr.File(
                        label="📊 Upload Match Analytics (JSON)",
                        file_types=[".json"]
                    )

                    load_btn = gr.Button("Load Match Data", variant="primary")
                    load_status = gr.Textbox(label="Status", interactive=False)

                    match_name_input = gr.Textbox(
                        label="Match Name",
                        placeholder="e.g., Tunisia vs Algeria"
                    )

                    language_select = gr.Radio(
                        choices=["en", "ar", "fr"],
                        value="en",
                        label="Language",
                        info="English, Arabic, French"
                    )

                    start_btn = gr.Button("Start Chat Session", variant="primary")

                with gr.Column(scale=2):
                    gr.Markdown("### Chat with AI Coach")

                    chatbot = gr.Chatbot(
                        height=500,
                        label="Conversation",
                        avatar_images=("👤", "🤖")
                    )

                    with gr.Row():
                        msg_input = gr.Textbox(
                            label="Your Question",
                            placeholder="Ask anything about the match...",
                            scale=4
                        )
                        send_btn = gr.Button("Send", variant="primary", scale=1)

                    gr.Markdown("### Example Questions")
                    gr.Markdown("""
- Who was the best performing player?
- What are our main tactical weaknesses?
- Which players showed signs of fatigue?
- How can we improve our passing game?
- What formation should we use next match?
""")

        with gr.Tab("📝 Match Narrative"):
            gr.Markdown("### Automatic Match Summary")

            narrative_lang = gr.Radio(
                choices=["en", "ar", "fr"],
                value="en",
                label="Language"
            )

            generate_narrative_btn = gr.Button("Generate Narrative", variant="primary")

            narrative_output = gr.Textbox(
                label="Match Narrative",
                lines=15,
                interactive=False
            )

        with gr.Tab("📋 Tactical Recommendations"):
            gr.Markdown("### AI-Generated Tactical Advice")

            rec_lang = gr.Radio(
                choices=["en", "ar", "fr"],
                value="en",
                label="Language"
            )

            generate_rec_btn = gr.Button("Generate Recommendations", variant="primary")

            rec_output = gr.Textbox(
                label="Recommendations",
                lines=15,
                interactive=False
            )

        with gr.Tab("ℹ️ About"):
            gr.Markdown("""
## 🤖 AI Coach Assistant

**Powered by Claude Sonnet 4.5** - Anthropic's most advanced AI model

### Features:
- ✅ **Natural Language Q&A**: Ask questions in plain language
- ✅ **Multi-language Support**: English, Arabic, French
- ✅ **Match Narratives**: Automatic professional match summaries
- ✅ **Tactical Recommendations**: Data-driven coaching advice
- ✅ **Context-Aware**: Understands all match analytics (xG, formations, fatigue, etc.)
- ✅ **Jersey Number Recognition**: References players by their shirt numbers

### How to Use:
1. Upload your match analytics JSON file
2. Click "Load Match Data"
3. Enter match name and select language
4. Click "Start Chat Session"
5. Ask questions or generate narratives/recommendations

### Supported Analytics:
- Basic stats (distance, speed, possession)
- Team metrics (passes, shots, events)
- Formations (8 formation types)
- Fatigue analysis (workload, sprint counting)
- Expected Goals (xG)
- Player valuations
- Injury risk predictions
- Opposition scouting reports

### Technical Details:
- **Model**: Claude Sonnet 4.5 (claude-sonnet-4-20250514)
- **Max Tokens**: 2048 per response
- **API**: Anthropic API or CLI fallback
- **Languages**: English (en), Arabic (ar), French (fr)

### Setup:
```bash
# Install Anthropic SDK
pip install anthropic

# Set API key
export ANTHROPIC_API_KEY='your-key-here'

# Or use Claude CLI from .bashrc
```

---

**Tunisia Football AI** - The most advanced football analysis system for coaches 🇹🇳⚽
""")

        # Event handlers
        def load_match(file):
            if file is None:
                return "❌ No file selected"
            return chat_interface.load_match_data(file.name)

        def start_session(match_name, language):
            status, history = chat_interface.start_chat(match_name, language)
            return history, status

        def send_message(message, history, language):
            new_history, _ = chat_interface.chat(message, history, language)
            return new_history, ""

        # Connect events
        load_btn.click(load_match, inputs=[analytics_file], outputs=[load_status])

        start_btn.click(
            start_session,
            inputs=[match_name_input, language_select],
            outputs=[chatbot, load_status]
        )

        msg_input.submit(
            send_message,
            inputs=[msg_input, chatbot, language_select],
            outputs=[chatbot, msg_input]
        )

        send_btn.click(
            send_message,
            inputs=[msg_input, chatbot, language_select],
            outputs=[chatbot, msg_input]
        )

        generate_narrative_btn.click(
            chat_interface.generate_narrative,
            inputs=[narrative_lang],
            outputs=[narrative_output]
        )

        generate_rec_btn.click(
            chat_interface.generate_recommendations,
            inputs=[rec_lang],
            outputs=[rec_output]
        )

    return interface


def main():
    """Launch coach chat interface"""
    print("🤖 Launching AI Coach Assistant Interface...")

    interface = create_interface()

    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
