"""Gradio UI for multi-model assisted assignment preparation.

This module provides an interface that covers the following requirements:

1. Extract text from an uploaded PDF (or text file), including optional OCR for mixed Korean/Chinese pages and embedded images.
2. Run a four-round multi-agent deliberation to refine Korean-language summary angles.
3. Produce an initial Korean draft via Claude-4.5 Sonnet for the selected focus.
4. Refine the draft with GPT-5 Medium while preserving tone and nuance.
5. Evaluate the refined draft with Gemini 2.5 Pro for human-likeness signals.
6. Produce a final Korean summary with Claude-4.5 Sonnet that incorporates Gemini's feedback.
7. Track tool invocation history and expose each step to the user.

Run `python gradio_assignment_builder.py` to launch the Gradio Blocks UI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import gradio as gr

from get_api_key import get_api_key


OPENAI_TOPIC_MODEL = "gpt-4.1-mini"
CLAUDE_TOPIC_MODEL = "claude-3-5-haiku-latest"
GEMINI_TOPIC_MODEL = "gemini-2.5-flash-lite"

CLAUDE_PREMIUM_MODEL = "claude-sonnet-4-5-20250929"
OPENAI_PREMIUM_MODEL = "gpt-5"
GEMINI_PREMIUM_MODEL = "gemini-2.5-pro"

MAX_SOURCE_CHARS = 6000
TOPIC_DISCUSSION_ROUNDS = 2


@dataclass
class Tool:
    """Helper that represents a single pipeline tool."""

    name: str
    description: str
    func: Callable

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def extract_text_from_file(file_obj) -> Tuple[str, str]: #(강제성은 없지만) return 값을 미리 선언해 잠재적 오류를 줄임
    """Extract text content from a PDF or plain-text file."""

    if file_obj is None:
        return "", "No file uploaded."

    file_path = getattr(file_obj, "name", None) or file_obj
    if not os.path.exists(file_path):
        return "", "Unable to resolve the uploaded file path."

    _, ext = os.path.splitext(file_path.lower())

    status_notes: List[str] = []
    ocr_text = ""

    if ext == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:  # pragma: no cover
            return "", "Missing dependency: install `pypdf` and retry."

        try:
            reader = PdfReader(file_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
        except Exception as exc:  # pragma: no cover - PDF read failure fallback
            return "", f"Failed to read PDF: {exc}"

        page_total = len(getattr(reader, "pages", []))
        ocr_limit = min(3, page_total) if page_total else 3
        ocr_text, ocr_status = attempt_pdf_ocr(file_path, ocr_limit)
        status_notes.append(ocr_status)
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as handle:
                text = handle.read()
        except Exception as exc:  # pragma: no cover
            return "", f"Failed to open text file: {exc}"

    text = text.strip()
    if not text and not ocr_text:
        return "", "No text could be extracted from the file."

    combined_source = text
    if ocr_text:
        combined_source = f"{combined_source}\n\n[Image OCR]\n{ocr_text}" if combined_source else f"[Image OCR]\n{ocr_text}"

    truncated = False
    if len(combined_source) > MAX_SOURCE_CHARS:
        combined_source = combined_source[:MAX_SOURCE_CHARS]
        truncated = True

    status_notes.insert(0, "Text extraction completed.")
    if truncated:
        status_notes.append(f"Source truncated to {MAX_SOURCE_CHARS} characters for prompting.")

    final_status = " ".join(note for note in status_notes if note)

    return combined_source, final_status or "Text extraction completed."


def parse_topics(raw: str) -> List[str]:
    """Parse a topic list safely from a model response."""

    cleaned = raw.strip()

    try:
        topics = json.loads(cleaned)
        if isinstance(topics, list) and all(isinstance(item, str) for item in topics):
            return topics[:3]
    except json.JSONDecodeError:
        pass

    fallback: List[str] = []
    for line in cleaned.splitlines():
        line = line.strip(" -\t\n\r")
        if not line:
            continue
        if line[0].isdigit() and "." in line:
            line = line.split(".", 1)[1].strip()
        fallback.append(line)
        if len(fallback) == 3:
            break
    return fallback


def format_history(history: List[Tuple[str, str]]) -> str:
    if not history:
        return "No conversation history yet."
    lines = [f"**{speaker}**: {message}" for speaker, message in history]
    return "\n\n".join(lines)


def format_status_log(status_log: List[str]) -> str:
    if not status_log:
        return "Idle. Trigger a step to see live updates."
    return "\n".join([f"{idx + 1}. {entry}" for idx, entry in enumerate(status_log)])


def attempt_pdf_ocr(file_path: str, max_pages: int) -> Tuple[str, str]:
    """Run OCR on early PDF pages to capture image-based Korean/Chinese text."""

    if max_pages <= 0:
        return "", "Image OCR skipped: no pages requested."

    try:
        from pdf2image import convert_from_path  # type: ignore
    except ImportError:
        return "", "Image OCR skipped: install `pdf2image` and `pytesseract` to process embedded images."

    try:
        import pytesseract  # type: ignore
    except ImportError:
        return "", "Image OCR skipped: install `pytesseract` to process embedded images."

    try:
        images = convert_from_path(file_path, fmt="png", first_page=1, last_page=max_pages)
    except Exception as exc:  # pragma: no cover - poppler or rendering failures
        return "", f"Image OCR failed during PDF rendering: {exc}"

    ocr_chunks: List[str] = []
    for idx, image in enumerate(images, start=1):
        try:
            text = pytesseract.image_to_string(image, lang="kor+chi_sim+eng")
        except pytesseract.TesseractNotFoundError:  # type: ignore[attr-defined]
            return "", "Image OCR skipped: Tesseract executable not found on the system."
        except Exception as exc:  # pragma: no cover - OCR failure fallback
            ocr_chunks.append(f"[Page {idx} OCR error: {exc}]")
            continue

        cleaned = text.strip()
        if cleaned:
            ocr_chunks.append(f"[Page {idx}] {cleaned}")

    if not ocr_chunks:
        return "", f"Image OCR attempted on {len(images)} page(s) but produced no readable text."

    combined = "\n\n".join(ocr_chunks)
    return combined, f"Image OCR completed on {len(ocr_chunks)} snippet(s) across {len(images)} page(s)."


def format_discussion(discussion: List[Tuple[str, str]]) -> str:
    if not discussion:
        return "Summary deliberation has not started yet."
    return "\n\n".join([f"**{speaker}**: {message}" for speaker, message in discussion])


def build_claude_prompt(topic: str, requirements: str, source_text: str) -> List[Dict[str, str]]:
    system_prompt = (
        "You are a humanities teaching assistant who writes concise yet rich lecture summaries in Korean. "
        "Blend insights from Korean commentary, original Chinese passages, and visual cues when present. "
        "Maintain a warm but academic tone and ensure the output is entirely in Korean."
    )

    user_prompt = (
        f"[Selected Focus]\n{topic}\n\n"
        f"[Assignment Requirements]\n{requirements or '(No explicit requirements provided)'}\n\n"
        f"[Reference Notes]\n{source_text[:MAX_SOURCE_CHARS]}\n\n"
        "Summarize what the student learned in class today about Chinese literature, highlighting any referenced poems or imagery."
        " Aim for 4-5 paragraphs (roughly 450-600 Korean words) and conclude with a sentence linking the lesson to the student's perspective."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_openai_enhance_prompt(draft_text: str) -> List[Dict[str, str]]:
    system_prompt = (
        "You polish Korean-language academic summaries. "
        "Preserve factual accuracy and the author's voice while improving flow, transitions, and descriptive richness."
    )

    user_prompt = (
        "Refine the following Korean summary. Return only the revised Korean text without additional commentary.\n\n"
        f"[Draft]\n{draft_text}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_gemini_review_prompt(final_text: str, topic: str) -> List[Dict[str, str]]:
    system_prompt = (
        "You evaluate essays for human authenticity. "
        "Assess whether the writing feels overly machine-generated and offer mitigation tips."
    )

    user_prompt = (
        f"[Essay Topic]\n{topic}\n\n"
        f"[Final Draft]\n{final_text}\n\n"
        "Respond succinctly with:\n"
        "1) Overall naturalness (score 1-5)\n"
        "2) Potential AI tells\n"
        "3) Suggestions to sound more human\n"
        "Answer in Korean so the student can read it directly."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_final_prompt(
    refined_text: str,
    review_text: str,
    topic: str,
    requirements: str,
    source_text: str,
) -> List[Dict[str, str]]:
    system_prompt = (
        "You are an experienced essayist crafting polished Korean-language summaries for humanities seminars. "
        "Incorporate peer feedback gracefully, highlight thematic through-lines, and maintain a natural Korean voice."
    )

    user_prompt = (
        f"[Selected Focus]\n{topic or '(No specific focus selected)'}\n\n"
        f"[Assignment Requirements]\n{requirements or '(No explicit requirements provided)'}\n\n"
        f"[Refined Draft]\n{refined_text}\n\n"
        f"[Gemini Review]\n{review_text}\n\n"
        f"[Reference Excerpts]\n{source_text[:MAX_SOURCE_CHARS]}\n\n"
        "Revise the refined draft into a final Korean summary. Integrate actionable feedback from the Gemini review,"
        " emphasize key insights from both Korean and Chinese sources discussed in class, acknowledge notable imagery if described,"
        " and end with 1-2 reflective sentences on how the lesson deepens understanding of Chinese literature."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def create_app():
    openai_client, anthropic_client, gemini_client = get_api_key()

    claude_tool = Tool(
        name="draft_writer",
        description="Generate a Claude draft for the selected topic",
        func=lambda topic, requirements, source_text: anthropic_client.chat.completions.create(
            model=CLAUDE_PREMIUM_MODEL,
            messages=build_claude_prompt(topic, requirements, source_text),
        ),
    )

    enhance_tool = Tool(
        name="creative_editor",
        description="Polish the draft with an OpenAI model",
        func=lambda draft_text: openai_client.chat.completions.create(
            model=OPENAI_PREMIUM_MODEL,
            messages=build_openai_enhance_prompt(draft_text),
        ),
    )

    review_tool = Tool(
        name="ai_style_reviewer",
        description="Check AI-likeness with Gemini",
        func=lambda final_text, topic: gemini_client.chat.completions.create(
            model=GEMINI_PREMIUM_MODEL,
            messages=build_gemini_review_prompt(final_text, topic),
        ),
    )

    final_tool = Tool(
        name="final_integrator",
        description="Craft the final Korean summary with Claude using Gemini's feedback",
        func=lambda refined_text, review_text, topic, requirements, source_text: anthropic_client.chat.completions.create(
            model=CLAUDE_PREMIUM_MODEL,
            messages=build_final_prompt(refined_text, review_text, topic, requirements, source_text),
        ),
    )

    def handle_generate_topics(file_obj, requirements, history, doc_state):
        history = history or []
        doc_state = doc_state or {}
        status_log: List[str] = []
        discussion_log: List[Tuple[str, str]] = []

        def update_status(message: str) -> str:
            status_log.append(message)
            return format_status_log(status_log)

        def conversation_text() -> str:
            if not discussion_log:
                return "No discussion yet."
            return "\n".join([f"{speaker}: {message}" for speaker, message in discussion_log])

        source_text, status = extract_text_from_file(file_obj)
        history.append(("Document Reader", status))
        status_message = update_status("Processing uploaded document...")
        yield (
            "Preparing topic deliberation...",
            gr.update(choices=[], value=None, interactive=False),
            format_discussion(discussion_log),
            format_history(history),
            history,
            doc_state,
            status_message,
        )

        if not source_text:
            yield (
                "Upload a valid file before requesting summary focuses.",
                gr.update(choices=[], value=None, interactive=False),
                format_discussion(discussion_log),
                format_history(history),
                history,
                doc_state,
                update_status("Summary deliberation aborted: no readable text found."),
            )
            return

        requirements_text = requirements.strip() or "(No assignment requirements were provided)"
        truncated_source = source_text[:MAX_SOURCE_CHARS]

        doc_state.update(
            {
                "source_text": source_text,
                "requirements": requirements,
                "file_name": getattr(file_obj, "orig_name", getattr(file_obj, "name", "Uploaded File")),
            }
        )

        agents = [
            {
                "name": "OpenAI Strategist",
                "client": openai_client,
                "model": OPENAI_TOPIC_MODEL,
                "system_prompt": (
                    "You are the OpenAI Strategist. You analyze alignment between assignment requirements and high-impact research angles. "
                    "Reference previous ideas directly, point out strengths or risks, and propose 1-2 precise topic titles each turn. "
                    "Respond in Korean so the student can follow the discussion."
                ),
            },
            {
                "name": "Claude Visionary",
                "client": anthropic_client,
                "model": CLAUDE_TOPIC_MODEL,
                "system_prompt": (
                    "You are the Claude Visionary. You champion originality, narrative hooks, and maker-centric insights. "
                    "Push the conversation toward distinctive perspectives and supply 1-2 provocative topic titles each turn. "
                    "Respond in Korean so the student can follow the discussion."
                ),
            },
            {
                "name": "Gemini Pragmatist",
                "client": gemini_client,
                "model": GEMINI_TOPIC_MODEL,
                "system_prompt": (
                    "You are the Gemini Pragmatist. You stress-test feasibility, evidence availability, and academic rigor. "
                    "Identify practical concerns, reinforce viable angles, and offer 1-2 grounded topic titles each turn. "
                    "Respond in Korean so the student can follow the discussion."
                ),
            },
        ]

        hard_rules = (
            "HARD RULES:\n"
            "1) No stage directions or gestures.\n"
            "2) Stay fully in persona; do not mention being an AI model.\n"
            "3) Cite or critique earlier comments explicitly.\n"
            "4) Respond entirely in Korean."
        )

        status_message = update_status("Document parsed. Launching multi-agent deliberation...")
        yield (
            "Multi-agent deliberation has started...",
            gr.update(choices=[], value=None, interactive=False, visible=False),
            format_discussion(discussion_log),
            format_history(history),
            history,
            doc_state,
            status_message,
        )

        try:
            for round_index in range(TOPIC_DISCUSSION_ROUNDS):
                for agent in agents:
                    status_message = update_status(
                        f"Round {round_index + 1}: {agent['name']} is contributing..."
                    )
                    yield (
                        "Deliberation in progress...",
                        gr.update(choices=[], value=None, interactive=False, visible=False),
                        format_discussion(discussion_log),
                        format_history(history),
                        history,
                        doc_state,
                        status_message,
                    )

                    user_prompt = (
                        f"Assignment requirements:\n{requirements_text}\n\n"
                        f"Source excerpt (truncated):\n{truncated_source}\n\n"
                        f"Discussion so far:\n{conversation_text()}\n\n"
                        f"Respond as {agent['name']} in round {round_index + 1}."
                        " Critique prior suggestions, highlight opportunities or risks, and add 1-2 concise summary-focus titles with rationale."
                        " Prioritize angles that help a Korean-language recap of today's Chinese literature class, referencing Chinese poems or notable images when relevant."
                        " Reply entirely in Korean."
                    )

                    response = agent["client"].chat.completions.create(
                        model=agent["model"],
                        messages=[
                            {"role": "system", "content": agent["system_prompt"] + "\n" + hard_rules},
                            {"role": "user", "content": user_prompt},
                        ],
                    )
                    content = response.choices[0].message.content
                    discussion_log.append((agent["name"], content))

                    yield (
                        "Deliberation in progress...",
                        gr.update(choices=[], value=None, interactive=False, visible=False),
                        format_discussion(discussion_log),
                        format_history(history),
                        history,
                        doc_state,
                        update_status(
                            f"Round {round_index + 1}: {agent['name']} response logged."
                        ),
                    )

            status_message = update_status("Moderator synthesizing final summary focuses...")
            yield (
                "Synthesizing final summary focuses...",
                gr.update(choices=[], value=None, interactive=False, visible=False),
                format_discussion(discussion_log),
                format_history(history),
                history,
                doc_state,
                status_message,
            )

            moderator_prompt = (
                f"Assignment requirements:\n{requirements_text}\n\n"
                f"Source excerpt (truncated):\n{truncated_source}\n\n"
                f"Discussion transcript:\n{conversation_text()}\n\n"
                "Synthesize the debate into the three strongest, mutually distinct summary focuses."
                " Return a JSON array of Korean strings; each string may include a short clarifying phrase after the focus title."
            )

            summary_response = openai_client.chat.completions.create(
                model=OPENAI_TOPIC_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the neutral moderator summarizing a multi-agent debate."
                            " Output only the agreed top three summary focuses as a JSON array of Korean strings."
                        ),
                    },
                    {"role": "user", "content": moderator_prompt},
                ],
            )

            topics = parse_topics(summary_response.choices[0].message.content)
        except Exception as exc:  # pragma: no cover - guard against API failures
            history.append(("Summary Deliberation", f"Encountered an error: {exc}"))
            yield (
                "Failed to complete summary deliberation. Check the logs for details.",
                gr.update(choices=[], value=None, interactive=False, visible=False),
                format_discussion(discussion_log),
                format_history(history),
                history,
                doc_state,
                update_status("Summary deliberation failed: API error."),
            )
            return

        if not topics:
            history.append(("Summary Deliberation", "No summary focuses could be parsed from the moderator summary."))
            yield (
                "Summary focus synthesis failed. Provide more specific requirements and retry.",
                gr.update(choices=[], value=None, interactive=False, visible=False),
                format_discussion(discussion_log),
                format_history(history),
                history,
                doc_state,
                update_status("Summary deliberation failed: empty moderator response."),
            )
            return

        doc_state["topics"] = topics
        doc_state["topic_discussion"] = discussion_log
        formatted_topics = "\n".join([f"{idx+1}. {topic}" for idx, topic in enumerate(topics)])

        history.append(("Summary Deliberation", f"Three summary focuses agreed after {TOPIC_DISCUSSION_ROUNDS} rounds."))
        status_message = update_status("Summary focus deliberation completed.")

        yield (
            formatted_topics,
            gr.update(choices=topics, value=topics[0], interactive=True, visible=True),
            format_discussion(discussion_log),
            format_history(history),
            history,
            doc_state,
            status_message,
        )
        return

    def handle_build_draft(selected_topic, history, doc_state):
        history = history or []
        doc_state = doc_state or {}
        status_log: List[str] = []

        def update_status(message: str) -> str:
            status_log.append(message)
            return format_status_log(status_log)

        if not selected_topic:
            status_message = update_status("Draft pipeline aborted: no topic selected.")
            history.append(("System", "Select a topic before proceeding."))
            yield (
                "No topic selected.",
                "",
                "",
                "",
                format_history(history),
                history,
                doc_state,
                status_message,
            )
            return

        source_text = doc_state.get("source_text", "")
        requirements = doc_state.get("requirements", "")

        if not source_text:
            status_message = update_status("Draft pipeline aborted: missing source text.")
            history.append(("System", "Missing source text. Restart from the upload step."))
            yield (
                "Re-upload the document and regenerate summary focuses.",
                "",
                "",
                "",
                format_history(history),
                history,
                doc_state,
                status_message,
            )
            return

        status_message = update_status("Requesting draft from Claude-4.5 Sonnet...")
        yield (
            "Generating draft...",
            "",
            "",
            "",
            format_history(history),
            history,
            doc_state,
            status_message,
        )

        try:
            claude_response = claude_tool(selected_topic, requirements, source_text)
            claude_text = claude_response.choices[0].message.content
            history.append(("Claude Premium Drafter", "Draft completed."))
        except Exception as exc:  # pragma: no cover
            history.append(("Claude Premium Drafter", f"Error: {exc}"))
            status_message = update_status("Draft pipeline failed: Claude error.")
            yield (
                "Claude request failed.",
                "",
                "",
                "",
                format_history(history),
                history,
                doc_state,
                status_message,
            )
            return

        status_message = update_status("Draft received. Sending to GPT-5 Medium editor...")
        yield (
            claude_text,
            "Enhancing draft...",
            "",
            "",
            format_history(history),
            history,
            doc_state,
            status_message,
        )

        try:
            enhance_response = enhance_tool(claude_text)
            enhanced_text = enhance_response.choices[0].message.content
            history.append(("OpenAI Premium Editor", "Creative polish completed."))
        except Exception as exc:  # pragma: no cover
            history.append(("OpenAI Premium Editor", f"Error: {exc}"))
            status_message = update_status("Draft pipeline failed: OpenAI error.")
            yield (
                claude_text,
                "OpenAI request failed.",
                "",
                "",
                format_history(history),
                history,
                doc_state,
                status_message,
            )
            return

        status_message = update_status("Refined draft ready. Requesting Gemini 2.5 Pro review...")
        yield (
            claude_text,
            enhanced_text,
            "Review in progress...",
            "",
            format_history(history),
            history,
            doc_state,
            status_message,
        )

        try:
            review_response = review_tool(enhanced_text, selected_topic)
            review_text = review_response.choices[0].message.content
            history.append(("Gemini Premium Reviewer", "AI-likeness assessment completed."))
            status_message = update_status("Review complete. Integrating feedback with Claude-4.5 Sonnet...")
        except Exception as exc:  # pragma: no cover
            review_text = f"Gemini request failed: {exc}"
            history.append(("Gemini Premium Reviewer", review_text))
            status_message = update_status("Review step encountered an error; attempting final synthesis nonetheless.")

        yield (
            claude_text,
            enhanced_text,
            review_text,
            "Final synthesis in progress...",
            format_history(history),
            history,
            doc_state,
            status_message,
        )

        try:
            final_response = final_tool(
                enhanced_text,
                review_text,
                selected_topic,
                requirements,
                doc_state.get("source_text", ""),
            )
            final_text = final_response.choices[0].message.content
            history.append(("Claude Integrator", "Final Korean summary completed."))
            status_message = update_status("Draft pipeline completed successfully.")
        except Exception as exc:  # pragma: no cover
            final_text = f"Final synthesis failed: {exc}"
            history.append(("Claude Integrator", final_text))
            status_message = update_status("Final synthesis failed.")

        doc_state.update(
            {
                "selected_topic": selected_topic,
                "claude_draft": claude_text,
                "enhanced_text": enhanced_text,
                "review": review_text,
                "final_summary": final_text,
            }
        )

        yield (
            claude_text,
            enhanced_text,
            review_text,
            final_text,
            format_history(history),
            history,
            doc_state,
            status_message,
        )
        return

    with gr.Blocks(title="Assignment Builder Trio") as demo:
        gr.Markdown(
            """# Assignment Builder Trio

This app guides you from topic ideation to drafting, creative refinement, and AI-style review based on an uploaded resource.
            """
        )

        history_state = gr.State([])
        doc_state = gr.State({})

        with gr.Row():
            file_input = gr.File(label="Upload assignment materials (PDF preferred)", file_count="single")
            requirements_input = gr.Textbox(
                label="Assignment requirements (required)",
                placeholder="e.g., 2000 words, include case studies, comparative analysis",
                lines=6,
            )

        generate_button = gr.Button("Step 1: Generate summary focuses", variant="primary")

        topics_output = gr.Markdown("Summary focus options will appear here once generated.")
        topic_selector = gr.Radio(label="Select your preferred summary focus", choices=[], visible=False)
        discussion_output = gr.Markdown("Summary deliberation log will appear here.")

        build_button = gr.Button("Step 2: Draft, refine, review, and finalize")

        with gr.Tab("Draft"):
            claude_output = gr.Markdown("The Claude draft will be displayed here.")

        with gr.Tab("Creative revision"):
            enhanced_output = gr.Markdown("The OpenAI-enhanced draft will be displayed here.")

        with gr.Tab("AI-style review"):
            review_output = gr.Markdown("Gemini's assessment will be displayed here.")

        with gr.Tab("Final Korean summary"):
            final_output = gr.Markdown("The final Korean summary will be displayed here.")

        history_output = gr.Markdown("No conversation history yet.")
        status_output = gr.Markdown("Idle. Trigger a step to see live updates.")

        generate_button.click(
            handle_generate_topics,
            inputs=[file_input, requirements_input, history_state, doc_state],
            outputs=[
                topics_output,
                topic_selector,
                discussion_output,
                history_output,
                history_state,
                doc_state,
                status_output,
            ],
        )

        build_button.click(
            handle_build_draft,
            inputs=[topic_selector, history_state, doc_state],
            outputs=[
                claude_output,
                enhanced_output,
                review_output,
                final_output,
                history_output,
                history_state,
                doc_state,
                status_output,
            ],
        )

    return demo


if __name__ == "__main__":
    app = create_app()
    app.launch()


