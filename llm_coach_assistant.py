"""
LLM Coach Assistant - AI-Powered Football Analysis Chatbot
===========================================================

Integrates Claude Sonnet 4.5 for:
- Natural language Q&A about match analysis
- Automatic match narrative generation
- Tactical recommendations in plain language
- Interactive coaching conversations
- Multi-language support (English, Arabic, French)

Based on professional coaching methodologies + LLM intelligence.
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess

@dataclass
class ChatMessage:
    """Single chat message"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class CoachingSession:
    """Complete coaching conversation session"""
    session_id: str
    match_name: str
    messages: List[ChatMessage]
    created_at: str
    language: str = 'en'

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class LLMCoachAssistant:
    """
    AI Coach Assistant powered by Claude Sonnet 4.5
    """

    def __init__(self, language: str = 'en'):
        """
        Initialize LLM Coach Assistant

        Args:
            language: 'en' (English), 'ar' (Arabic), 'fr' (French)
        """
        self.language = language
        self.sessions = {}
        self.current_session_id = None

        # Check Claude availability
        self.claude_available = self._check_claude_available()

        # System prompts for different languages
        self.system_prompts = {
            'en': """You are an expert football (soccer) coach assistant analyzing match data.
You have access to comprehensive match analytics including:
- Player statistics (distance, speed, goals, assists)
- Team metrics (possession, passes, shots, formations)
- Tactical analysis (pressing, pass networks, formations)
- Advanced analytics (xG, player valuations, injury risk, opposition scouting)
- Jersey numbers (players identified by their shirt numbers)

Your role:
1. Answer questions about the match in clear, actionable language
2. Provide tactical insights and recommendations
3. Explain complex metrics in simple terms
4. Give coaching advice based on the data
5. Be concise but thorough

Always reference specific players by their jersey numbers (e.g., "Player #10") and provide data-driven insights.""",

            'ar': """أنت مساعد مدرب كرة قدم خبير تقوم بتحليل بيانات المباراة.
لديك إمكانية الوصول إلى تحليلات شاملة للمباراة بما في ذلك:
- إحصائيات اللاعبين (المسافة، السرعة، الأهداف، التمريرات الحاسمة)
- مقاييس الفريق (الاستحواذ، التمريرات، التسديدات، التشكيلات)
- التحليل التكتيكي (الضغط، شبكات التمرير، التشكيلات)
- التحليلات المتقدمة (xG، تقييمات اللاعبين، مخاطر الإصابة، مراقبة المنافس)
- أرقام القمصان (يتم تحديد اللاعبين بأرقام قمصانهم)

دورك:
1. الإجابة على الأسئلة حول المباراة بلغة واضحة وقابلة للتنفيذ
2. تقديم رؤى وتوصيات تكتيكية
3. شرح المقاييس المعقدة بمصطلحات بسيطة
4. تقديم نصائح تدريبية بناءً على البيانات
5. كن موجزاً ولكن شاملاً

ارجع دائماً إلى لاعبين محددين بأرقام قمصانهم (مثل "اللاعب رقم 10") وقدم رؤى مدفوعة بالبيانات.""",

            'fr': """Vous êtes un assistant expert en entraînement de football analysant les données de match.
Vous avez accès à des analyses complètes du match incluant:
- Statistiques des joueurs (distance, vitesse, buts, passes décisives)
- Métriques d'équipe (possession, passes, tirs, formations)
- Analyse tactique (pressing, réseaux de passes, formations)
- Analyses avancées (xG, valorisations des joueurs, risque de blessure, observation des adversaires)
- Numéros de maillot (joueurs identifiés par leurs numéros de maillot)

Votre rôle:
1. Répondre aux questions sur le match dans un langage clair et actionnable
2. Fournir des insights et recommandations tactiques
3. Expliquer les métriques complexes en termes simples
4. Donner des conseils d'entraînement basés sur les données
5. Être concis mais complet

Référencez toujours des joueurs spécifiques par leurs numéros de maillot (par exemple, "Joueur #10") et fournissez des insights basés sur les données."""
        }

    def _check_claude_available(self) -> bool:
        """Check if Claude is available in environment"""
        try:
            # Check if claude command exists in PATH
            result = subprocess.run(
                ['which', 'claude'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Claude CLI found in PATH")
                return True

            # Check for ANTHROPIC_API_KEY
            if os.getenv('ANTHROPIC_API_KEY'):
                print("✅ ANTHROPIC_API_KEY found in environment")
                return True

            print("⚠️  Claude not found. Install with: pip install anthropic")
            return False

        except Exception as e:
            print(f"⚠️  Error checking Claude: {e}")
            return False

    def _call_claude(self, prompt: str, system_prompt: str = None) -> str:
        """
        Call Claude Sonnet 4.5 API

        Args:
            prompt: User prompt
            system_prompt: System context

        Returns:
            Claude's response
        """
        if not self.claude_available:
            return self._fallback_response(prompt)

        try:
            # Try using Anthropic Python SDK
            try:
                import anthropic

                client = anthropic.Anthropic(
                    api_key=os.getenv('ANTHROPIC_API_KEY')
                )

                message = client.messages.create(
                    model="claude-sonnet-4-20250514",  # Claude Sonnet 4.5
                    max_tokens=2048,
                    system=system_prompt or self.system_prompts[self.language],
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                return message.content[0].text

            except ImportError:
                # Fallback to CLI if SDK not available
                print("⚠️  Anthropic SDK not found, using CLI fallback")
                return self._call_claude_cli(prompt, system_prompt)

        except Exception as e:
            print(f"❌ Claude API error: {e}")
            return self._fallback_response(prompt)

    def _call_claude_cli(self, prompt: str, system_prompt: str = None) -> str:
        """Call Claude using CLI (from .bashrc)"""
        try:
            # Prepare full prompt
            full_prompt = f"{system_prompt or self.system_prompts[self.language]}\n\nUser: {prompt}\n\nAssistant:"

            # Call Claude CLI
            result = subprocess.run(
                ['bash', '-c', f'source ~/.bashrc && echo "{full_prompt}" | claude'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return self._fallback_response(prompt)

        except Exception as e:
            print(f"❌ Claude CLI error: {e}")
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        """Fallback response when Claude is not available"""
        fallback_responses = {
            'en': """I'm currently running in offline mode. To enable full AI analysis, please:
1. Install the Anthropic SDK: pip install anthropic
2. Set your API key: export ANTHROPIC_API_KEY='your-key-here'

For now, I can help you understand the match data. What specific aspect would you like to analyze?""",

            'ar': """أنا حالياً في وضع عدم الاتصال. لتمكين التحليل الكامل بالذكاء الاصطناعي، يرجى:
1. تثبيت Anthropic SDK: pip install anthropic
2. تعيين مفتاح API الخاص بك: export ANTHROPIC_API_KEY='your-key-here'

في الوقت الحالي، يمكنني مساعدتك في فهم بيانات المباراة. ما الجانب المحدد الذي تريد تحليله؟""",

            'fr': """Je fonctionne actuellement en mode hors ligne. Pour activer l'analyse IA complète, veuillez:
1. Installer le SDK Anthropic: pip install anthropic
2. Définir votre clé API: export ANTHROPIC_API_KEY='your-key-here'

Pour l'instant, je peux vous aider à comprendre les données du match. Quel aspect spécifique souhaitez-vous analyser?"""
        }

        return fallback_responses.get(self.language, fallback_responses['en'])

    def start_session(self, match_name: str, analytics_data: Dict) -> str:
        """
        Start a new coaching session

        Args:
            match_name: Name of the match
            analytics_data: Complete match analytics

        Returns:
            session_id
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        session = CoachingSession(
            session_id=session_id,
            match_name=match_name,
            messages=[],
            created_at=datetime.now().isoformat(),
            language=self.language
        )

        self.sessions[session_id] = session
        self.current_session_id = session_id

        # Store analytics data for this session
        session.analytics_data = analytics_data

        print(f"✅ Started coaching session: {session_id}")
        return session_id

    def ask_question(self, question: str, session_id: str = None) -> str:
        """
        Ask a question about the match

        Args:
            question: User's question
            session_id: Session ID (uses current if None)

        Returns:
            Assistant's response
        """
        session_id = session_id or self.current_session_id

        if session_id not in self.sessions:
            return "Error: No active session. Please start a session first."

        session = self.sessions[session_id]

        # Add user message
        user_msg = ChatMessage(role='user', content=question)
        session.messages.append(user_msg)

        # Prepare context with match data
        context = self._prepare_context(session.analytics_data)

        # Build full prompt
        full_prompt = f"{context}\n\nUser Question: {question}\n\nProvide a clear, actionable answer based on the match data above."

        # Get response from Claude
        response = self._call_claude(full_prompt)

        # Add assistant message
        assistant_msg = ChatMessage(role='assistant', content=response)
        session.messages.append(assistant_msg)

        return response

    def _prepare_context(self, analytics_data: Dict) -> str:
        """Prepare match context for Claude"""

        # Extract key information
        team_stats = analytics_data.get('team_stats', {})
        player_stats = analytics_data.get('player_stats', [])

        # Format context
        context = f"""Match Analysis Data:

TEAM STATISTICS:
Team 1: {team_stats.get('team_1', {}).get('possession_percent', 0):.1f}% possession, {team_stats.get('team_1', {}).get('total_passes', 0)} passes, {team_stats.get('team_1', {}).get('total_shots', 0)} shots
Team 2: {team_stats.get('team_2', {}).get('possession_percent', 0):.1f}% possession, {team_stats.get('team_2', {}).get('total_passes', 0)} passes, {team_stats.get('team_2', {}).get('total_shots', 0)} shots

TOP PLAYERS (by distance):"""

        for i, player in enumerate(player_stats[:5], 1):
            player_name = player.get('player_name', f"Player ID {player.get('player_id')}")
            context += f"\n{i}. {player_name} (Team {player.get('team')}): {player.get('total_distance_m', 0):.1f}m, Max speed: {player.get('max_speed_kmh', 0):.1f} km/h"

        # Add Level 3 data if available
        if 'formations' in analytics_data:
            context += f"\n\nFORMATIONS:"
            formations = analytics_data['formations']
            for team_id, formation_data in formations.items():
                context += f"\nTeam {team_id}: {formation_data.get('formation_name', 'Unknown')}"

        if 'alerts' in analytics_data:
            alerts = analytics_data['alerts']
            if alerts:
                context += f"\n\nTACTICAL ALERTS ({len(alerts)} total):"
                for alert in alerts[:3]:
                    context += f"\n- {alert.get('title', '')}: {alert.get('description', '')}"

        # Add Level 4 data if available
        if 'xg_analysis' in analytics_data:
            xg = analytics_data['xg_analysis']
            context += f"\n\nEXPECTED GOALS (xG):"
            context += f"\nTeam 1: {xg.get('team1_xg', 0)} xG ({xg.get('team1_shots', 0)} shots)"
            context += f"\nTeam 2: {xg.get('team2_xg', 0)} xG ({xg.get('team2_shots', 0)} shots)"

        if 'injury_risk_team1' in analytics_data:
            injury1 = analytics_data['injury_risk_team1']
            high_risk = injury1.get('high_risk_players', [])
            if high_risk:
                context += f"\n\nINJURY RISK (Team 1):"
                for player in high_risk[:2]:
                    context += f"\n- {player.get('name', 'Unknown')}: {player.get('risk_score', 0)}/100 risk"

        return context

    def generate_match_narrative(self, analytics_data: Dict) -> str:
        """
        Generate automatic match narrative

        Args:
            analytics_data: Complete match analytics

        Returns:
            Narrative text
        """
        context = self._prepare_context(analytics_data)

        narrative_prompts = {
            'en': f"""{context}

Generate a comprehensive 3-paragraph match narrative covering:
1. Overall match flow and key statistics
2. Standout individual performances
3. Tactical insights and recommendations for improvement

Write in the style of a professional football analyst.""",

            'ar': f"""{context}

قم بإنشاء سرد شامل للمباراة من 3 فقرات يغطي:
1. سير المباراة العام والإحصائيات الرئيسية
2. الأداء الفردي المتميز
3. الرؤى التكتيكية والتوصيات للتحسين

اكتب بأسلوب محلل كرة قدم محترف.""",

            'fr': f"""{context}

Générez un récit de match complet en 3 paragraphes couvrant:
1. Le déroulement général du match et les statistiques clés
2. Les performances individuelles exceptionnelles
3. Les insights tactiques et recommandations d'amélioration

Écrivez dans le style d'un analyste de football professionnel."""
        }

        prompt = narrative_prompts.get(self.language, narrative_prompts['en'])

        narrative = self._call_claude(prompt)

        return narrative

    def generate_tactical_recommendations(self, analytics_data: Dict) -> List[str]:
        """
        Generate tactical recommendations

        Args:
            analytics_data: Complete match analytics

        Returns:
            List of recommendations
        """
        context = self._prepare_context(analytics_data)

        rec_prompts = {
            'en': f"""{context}

Based on this match data, provide 5 specific tactical recommendations for improvement.
Format as a numbered list. Be concise and actionable.""",

            'ar': f"""{context}

بناءً على بيانات هذه المباراة، قدم 5 توصيات تكتيكية محددة للتحسين.
قم بالتنسيق كقائمة مرقمة. كن موجزاً وقابلاً للتنفيذ.""",

            'fr': f"""{context}

Sur la base de ces données de match, fournissez 5 recommandations tactiques spécifiques pour l'amélioration.
Formatez comme une liste numérotée. Soyez concis et actionnable."""
        }

        prompt = rec_prompts.get(self.language, rec_prompts['en'])

        response = self._call_claude(prompt)

        # Parse into list
        recommendations = [line.strip() for line in response.split('\n') if line.strip() and line[0].isdigit()]

        return recommendations

    def get_session_history(self, session_id: str = None) -> List[Dict]:
        """Get conversation history for a session"""
        session_id = session_id or self.current_session_id

        if session_id not in self.sessions:
            return []

        session = self.sessions[session_id]
        return [asdict(msg) for msg in session.messages]

    def export_session(self, session_id: str, output_path: str):
        """Export session to JSON"""
        if session_id not in self.sessions:
            print(f"❌ Session {session_id} not found")
            return

        session = self.sessions[session_id]

        session_data = {
            'session_id': session.session_id,
            'match_name': session.match_name,
            'created_at': session.created_at,
            'language': session.language,
            'messages': [asdict(msg) for msg in session.messages]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Session exported to {output_path}")


def main():
    """Demo LLM Coach Assistant"""
    print("🤖 LLM Coach Assistant - Demo\n")

    # Initialize assistant
    assistant = LLMCoachAssistant(language='en')

    # Demo analytics data
    demo_analytics = {
        'team_stats': {
            'team_1': {'possession_percent': 58.5, 'total_passes': 450, 'total_shots': 12},
            'team_2': {'possession_percent': 41.5, 'total_passes': 320, 'total_shots': 8}
        },
        'player_stats': [
            {'player_id': 10, 'player_name': 'Player #10', 'team': 1, 'total_distance_m': 10523, 'max_speed_kmh': 32.5},
            {'player_id': 7, 'player_name': 'Player #7', 'team': 1, 'total_distance_m': 9876, 'max_speed_kmh': 30.1},
        ]
    }

    # Start session
    print("Starting coaching session...")
    session_id = assistant.start_session("Tunisia vs Opponent", demo_analytics)

    # Generate narrative
    print("\n📝 Generating match narrative...")
    narrative = assistant.generate_match_narrative(demo_analytics)
    print(f"\n{narrative}\n")

    # Generate recommendations
    print("\n📋 Generating tactical recommendations...")
    recommendations = assistant.generate_tactical_recommendations(demo_analytics)
    print("\nRecommendations:")
    for rec in recommendations:
        print(f"  {rec}")

    # Interactive Q&A demo
    print("\n💬 Interactive Q&A Demo:")
    demo_questions = [
        "Who was the best performing player?",
        "What tactical adjustments should we make?"
    ]

    for question in demo_questions:
        print(f"\nQ: {question}")
        answer = assistant.ask_question(question, session_id)
        print(f"A: {answer}")

    # Export session
    print("\n📤 Exporting session...")
    assistant.export_session(session_id, 'outputs/coaching_session.json')

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    main()
