SYSTEM_PROMPT_AR = """أنت مساعد ذكي متخصص في شهادة PMP (محترف إدارة المشاريع). مهمتك شرح إجابات أسئلة PMP باللغة العربية بأسلوب واضح ومبسط.

قواعد يجب اتباعها دائماً:
- اكتب الشرح كاملاً باللغة العربية
- المصطلحات التقنية تُكتب بالعربية مع المصطلح الإنجليزي بين قوسين: مثال: إدارة المخاطر (Risk Management)
- لا تخلط بين اتجاهي النص في الجملة الواحدة
- الأرقام والكود تبقى بالاتجاه الأيسر-لليمين دائماً
- لا تكرر السؤال في بداية شرحك
- اعطِ شرحاً عملياً يربط المفهوم بسيناريوهات حقيقية من بيئة العمل
- لا تذكر أنك ذكاء اصطناعي أو أي تفاصيل تقنية عن نفسك"""

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


def should_use_think_mode(question_stem: str) -> bool:
    """Return True for complex reasoning questions that benefit from chain-of-thought."""
    stem_lower = question_stem.lower()
    return any(kw in stem_lower for kw in _REASONING_KEYWORDS)


def build_user_message(
    question_stem: str,
    selected_option: int,
    context_chunks: list[str],
    use_think: bool,
) -> str:
    """Assemble the full user turn for Qwen3. Appends /no_think or /think suffix."""
    context_block = "\n---\n".join(context_chunks) if context_chunks else "لا يوجد سياق متاح."

    message = f"""السياق من مواد PMP:
---
{context_block}
---

السؤال: {question_stem}
الإجابة المختارة: الخيار {selected_option + 1}

اشرح لماذا هذه الإجابة صحيحة أو خاطئة مع ربطها بمعايير PMBOK ومجموعات العمليات ذات الصلة."""

    suffix = " /think" if use_think else " /no_think"
    return message + suffix
