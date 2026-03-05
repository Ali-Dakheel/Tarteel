SYSTEM_PROMPT_EN = """You are a PMP (Project Management Professional) exam tutor.

For every answer you MUST follow this format:
1. Start with "📖 From the reference:" and quote the EXACT verbatim text from the provided context (copy it word-for-word from the book).
2. If no relevant text is found in the context, explicitly say "No direct reference found in the provided materials."
3. Then briefly explain in 2-3 sentences how the quoted text answers the question.

Rules:
- Always quote verbatim from the context FIRST — never paraphrase the reference text
- Include the source and page number if visible in the context (e.g. [PMBOK-8th.pdf, p.12])
- Keep explanations concise and accurate to the source material
- Do not repeat the question
- Do not mention that you are an AI"""

SYSTEM_PROMPT_AR = """أنت مساعد متخصص في شهادة PMP (محترف إدارة المشاريع).

مهمتك في كل إجابة:
1. ابدأ بعبارة "📖 من المرجع:" واقتبس النص الحرفي من السياق المقدم (بالإنجليزية كما هو في الكتاب)
2. إذا لم يوجد نص مباشر في السياق، اذكر ذلك صراحةً
3. ثم اشرح باللغة العربية في 2-3 جمل كيف يجيب هذا النص على السؤال

قواعد:
- اقتبس النص الحرفي أولاً — لا تُعيد صياغة نص المرجع
- اذكر المصدر ورقم الصفحة إن وُجدا في السياق
- لا تكرر السؤال في بداية شرحك
- لا تذكر أنك ذكاء اصطناعي"""

_REASONING_KEYWORDS = [
    "best describes",
    "most appropriate",
    "which would",
    "compare",
    "contrast",
    "evaluate",
    "prioritize",
    "أفضل",
    "الأنسب",
    "قارن",
    "قيّم",
    "رتّب حسب الأولوية",
    "ما الذي يصف",
]


def detect_language(text: str) -> str:
    """Return 'ar' if >20% of characters are Arabic, else 'en'."""
    arabic_count = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
    return 'ar' if arabic_count / max(len(text), 1) > 0.2 else 'en'


def get_system_prompt(question_stem: str) -> str:
    """Return Arabic or English system prompt based on question language."""
    return SYSTEM_PROMPT_AR if detect_language(question_stem) == 'ar' else SYSTEM_PROMPT_EN


def should_use_think_mode(question_stem: str) -> bool:
    """Return True for complex reasoning questions that benefit from chain-of-thought."""
    stem_lower = question_stem.lower()
    return any(kw in stem_lower for kw in _REASONING_KEYWORDS)


def build_user_message(
    question_stem: str,
    selected_option: int | None,
    context_chunks: list[str],
    use_think: bool,
) -> str:
    """Assemble the full user turn for Qwen3. Appends /no_think or /think suffix."""
    context_block = "\n---\n".join(context_chunks) if context_chunks else "No context available."

    lang = detect_language(question_stem)

    if lang == 'ar':
        answer_line = (
            f"الإجابة المختارة: الخيار {selected_option + 1}"
            if selected_option is not None
            else "سؤال مفتوح من المتعلم."
        )
        message = f"""السياق من مواد PMP (اقتبس منه حرفياً):
---
{context_block}
---

السؤال: {question_stem}
{answer_line}

أولاً: اقتبس النص الحرفي ذات الصلة من السياق أعلاه (كما هو في الكتاب).
ثانياً: اشرح باللغة العربية كيف يرتبط هذا النص بالسؤال."""
    else:
        answer_line = (
            f"Selected answer: Option {selected_option + 1}"
            if selected_option is not None
            else "Open question from the learner."
        )
        message = f"""Context from PMP reference materials (quote verbatim):
---
{context_block}
---

Question: {question_stem}
{answer_line}

First: Quote the exact verbatim text from the context above that answers this question.
Second: Briefly explain how it answers the question."""

    suffix = " /think" if use_think else " /no_think"
    return message + suffix
