"""Agent2 evaluator for live interview preparation sessions."""

from __future__ import annotations

from typing import Any

from shared.runtime import create_agent

from .schemas import InterviewEvaluatorResult


SYSTEM_PROMPT = """\
You are a senior interview coach and hiring-signal evaluator.

Your job is to evaluate one completed interview practice session against the
candidate context, job analysis, interview knowledge base, and briefing.

You are strict but useful. Do not make a hire/no-hire recommendation. Create
preparation value: what worked, what failed, what to practice next, and what the
candidate should say more concretely next time.

Evaluation process:
1. Read all candidate context. Separate verified facts from speculation.
2. Read the job analysis and briefing. Extract what this interview must prove.
3. Read the transcript turn by turn. Evaluate only what the candidate actually said.
4. Quote evidence from the transcript. Do not invent quotes.
5. Penalize vague answers, missing examples, weak role motivation, and unaddressed
   fit gaps.
6. Reward concrete ownership, numbers, constraints, self-awareness, and strong
   questions back to the interviewer.
7. Produce a compact markdown report the user can study.

Rubric keys must be exactly:
- rollenfit
- motivation
- konkretheit
- schwaechen_umgang
- kommunikation
- domain_fit
- rueckfragenqualitaet

Risk level:
- low: candidate is broadly ready and mainly needs polish.
- medium: candidate has useful signals but meaningful gaps remain.
- high: candidate is not yet ready for a realistic interview on this role.

Output must conform exactly to the declared schema.
"""


agent = create_agent(
    name="interview-evaluator",
    output_type=InterviewEvaluatorResult,
    instructions=SYSTEM_PROMPT,
)


def mock_result(input_data: dict[str, Any]) -> dict[str, Any]:
    transcript = input_data.get("transcript") or []
    user_turns = [turn for turn in transcript if isinstance(turn, dict) and turn.get("speaker") == "user"]
    quote = "Noch keine Kandidatenantwort im Transcript."
    if user_turns:
        quote = str(user_turns[0].get("text") or quote)[:220]

    markdown = f"""# Interview Feedback Report

## Gesamturteil

Readiness Score: **58/100**
Risiko-Level: **medium**

## Wichtigstes Signal

Der Kandidat liefert erste auswertbare Antworten, muss aber konkreter werden.

## Evidenz

> {quote}

## Naechste Schritte

1. Drei STAR-Stories vorbereiten.
2. Rollenmotivation schaerfen.
3. Luecken offensiv und lernorientiert framen.
4. Rueckfragen aus der Jobanalyse ableiten.
5. Noch ein strenges Rollenspiel durchfuehren.
"""

    return {
        "readiness_score": 58,
        "risk_level": "medium",
        "strongest_selling_points": [
            "Das Interview liefert auswertbare Signale.",
            "Der Kandidat kann Antworten anhand des Briefings weiter schaerfen.",
        ],
        "scorecard": {
            "rollenfit": 60,
            "motivation": 55,
            "konkretheit": 52,
            "schwaechen_umgang": 55,
            "kommunikation": 64,
            "domain_fit": 58,
            "rueckfragenqualitaet": 50,
        },
        "evidence": {
            "strong_answers": [
                {
                    "quote": quote,
                    "why_it_worked": "Die Antwort kann als Ausgangspunkt fuer eine konkretere STAR-Story dienen.",
                }
            ],
            "weak_answers": [
                {
                    "quote": quote,
                    "improvement": "Mit Situation, Handlung, Ergebnis und Reflexion konkretisieren.",
                }
            ],
            "missed_opportunities": [
                "Jobanforderungen direkter mit eigenen Projekten verbinden.",
                "Motivation spezifischer auf Firma und Rolle beziehen.",
                "Rueckfragen strategischer vorbereiten.",
            ],
        },
        "action_plan": {
            "improvements": [
                "Eine 60-Sekunden-Motivation schreiben.",
                "Drei STAR-Beispiele fuer zentrale Anforderungen vorbereiten.",
                "Eine Schwäche als Lernkurve formulieren.",
                "Fuenf Rueckfragen aus Jobanalyse und Briefing ableiten.",
                "Das Interview im realistisch-strengen Modus wiederholen.",
            ],
            "drill_questions": [
                "Warum genau diese Rolle?",
                "Welches Projekt zeigt Ihre groesste relevante Staerke?",
                "Wo ist die groesste Luecke zu dieser Stelle?",
                "Wie gehen Sie mit Kritik oder Unsicherheit um?",
                "Welche Frage moechten Sie dem Unternehmen stellen?",
            ],
            "anki_cards": [
                {
                    "front": "Was ist die STAR-Struktur?",
                    "back": "Situation, Task, Action, Result plus kurze Reflexion.",
                }
            ],
        },
        "markdown": markdown,
    }
