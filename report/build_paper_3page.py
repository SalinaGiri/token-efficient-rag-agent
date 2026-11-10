"""3-page submission version (references excluded). Run make_figures.py first.
Text in grey boxes [like this] is a placeholder: replace it with your own content."""
import csv
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, Image, KeepTogether)
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

import os
# Times New Roman on macOS; Liberation Serif (same metrics) on Linux.
_MAC = "/System/Library/Fonts/Supplemental/Times New Roman"
_LIB = "/usr/share/fonts/truetype/liberation/LiberationSerif-"
_files = ({"TNR": _MAC + ".ttf", "TNR-B": _MAC + " Bold.ttf", "TNR-I": _MAC + " Italic.ttf", "TNR-BI": _MAC + " Bold Italic.ttf"}
          if os.path.exists(_MAC + ".ttf") else
          {"TNR": _LIB + "Regular.ttf", "TNR-B": _LIB + "Bold.ttf", "TNR-I": _LIB + "Italic.ttf", "TNR-BI": _LIB + "BoldItalic.ttf"})
for n, f in _files.items():
    pdfmetrics.registerFont(TTFont(n, f))
addMapping("TNR", 0, 0, "TNR"); addMapping("TNR", 1, 0, "TNR-B")
addMapping("TNR", 0, 1, "TNR-I"); addMapping("TNR", 1, 1, "TNR-BI")
BLACK, PH = colors.black, "#E4E4E4"

def S(name, **kw):
    d = dict(fontName="TNR", fontSize=12, leading=14.2, textColor=BLACK, alignment=TA_JUSTIFY)
    d.update(kw); return ParagraphStyle(name, **d)

body = S("body", spaceAfter=4)
bul = S("bul", leftIndent=14, bulletIndent=2, spaceAfter=2)
h1 = S("h1", fontName="TNR-B", fontSize=12.5, leading=15, alignment=TA_LEFT, spaceBefore=6, spaceAfter=3, keepWithNext=1)
tbl = S("tbl", fontSize=10, leading=11.8, alignment=TA_LEFT)
tblb = S("tblb", fontName="TNR-B", fontSize=10, leading=11.8, alignment=TA_LEFT)
cap = S("cap", fontSize=10, leading=12, alignment=TA_LEFT, spaceBefore=2, spaceAfter=5)
capk = S("capk", fontSize=10, leading=12, alignment=TA_LEFT, spaceAfter=2, keepWithNext=1)
abst = S("abst", fontSize=11, leading=13.2, leftIndent=0.6 * cm, rightIndent=0.6 * cm, spaceAfter=3)
ref = S("ref", fontSize=10.5, leading=12.8, alignment=TA_LEFT, leftIndent=24, firstLineIndent=-24, spaceAfter=3)

def P(t, st=body): return Paragraph(t, st)
def B(t): return Paragraph(t, bul, bulletText="•")
def ph(t): return f'<font backColor="{PH}"><i>[{t}]</i></font>'

PAGE_W, PAGE_H = A4
M = 2.0 * cm
W = PAGE_W - 2 * M

def T(rows, widths):
    data = [[P(c, tblb) for c in rows[0]]] + [[P(c, tblb if i == 0 else tbl) for i, c in enumerate(r)] for r in rows[1:]]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LINEABOVE", (0, 0), (-1, 0), 1.0, BLACK), ("LINEBELOW", (0, 0), (-1, 0), 0.6, BLACK),
                           ("LINEBELOW", (0, -1), (-1, -1), 1.0, BLACK),
                           ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return t

def img(path, width):
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=width, height=width * ih / iw)

def footer(c, doc):
    c.saveState(); c.setFont("TNR", 10)
    c.drawCentredString(PAGE_W / 2, 1.1 * cm, str(doc.page)); c.restoreState()

doc = BaseDocTemplate("Fewer_Better_Tokens_3page.pdf", pagesize=A4, leftMargin=M, rightMargin=M,
                      topMargin=M, bottomMargin=M, author="Salina Giri",
                      title="Fewer, Better Tokens: A Hardware-Aware Approach to Token Efficiency in an Operational Knowledge Assistant")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(M, M, W, PAGE_H - 2 * M, 0, 0, 0, 0)], onPage=footer)])

rows = list(csv.DictReader(open("results.csv", newline="")))
placeholder = any(r["placeholder"].strip().lower() == "yes" for r in rows)
def val(r, k, fmt="{:,.0f}"): return ph(" ") if placeholder else fmt.format(float(r[k]))

s = []
# ---------- Title block ----------
s += [P("Fewer, Better Tokens", S("t", fontName="TNR-B", fontSize=17, leading=21, alignment=TA_CENTER)),
      P("A Hardware-Aware Approach to Token Efficiency in an Operational Knowledge Assistant",
        S("st", fontName="TNR-I", fontSize=12.5, leading=16, alignment=TA_CENTER, spaceAfter=4)),
      P(f"Salina Giri · Applied Computer Science, UC Leuven-Limburg (UCLL), Belgium · November 2026<br/>"
        f"Technical exercise, internship 2026-INT-298 · Code and data: {ph('GitHub repository link')}",
        S("au", fontSize=10.5, leading=13, alignment=TA_CENTER, spaceAfter=6))]
rule = Table([[""]], colWidths=[W], rowHeights=[2]); rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.6, BLACK)]))
s.append(rule)

s.append(P(
    "<b>Abstract.</b> LLM inference runs in two phases with different hardware behaviour: a parallel, compute-bound "
    "<i>prefill</i> over input tokens and a sequential, memory-bandwidth-bound <i>decode</i> that generates output "
    "tokens [1, 2]. Most token-reduction work ignores this and counts every token as equal. This paper treats token "
    "efficiency as a hardware-aware design problem: it reviews five optimisation levers, selects one per phase "
    "(adaptive retrieval for input, output budgeting for output), and evaluates them in a five-variant ablation on 40 "
    "questions, including seven unanswerable ones. Two evaluation ideas are introduced: <i>tokens per correct cited "
    "answer</i> (TCCA) and a measured latency <i>exchange rate</i> between output and input tokens. "
    + ph("Key findings in one or two sentences."), abst))

# ---------- 1 ----------
s.append(P("1. Introduction", h1))
s.append(P(
    "An operational knowledge assistant sends the LLM system instructions, conversation history, retrieved passages "
    "and the user’s question, then receives a response. As the knowledge base and conversation grow, tokens per "
    "request rise, and with them cost, latency and energy. In agents the effect compounds, because context is re-sent "
    "at every step. Yet cutting tokens carelessly removes evidence or citations. This study asks: <b>(RQ1)</b> how far "
    "can input and output tokens be reduced while correctness stays within a pre-defined margin; <b>(RQ2)</b> do input "
    "and output tokens have different latency costs; and <b>(RQ3)</b> does adaptive retrieval improve correct "
    "abstention on unanswerable questions?"))

# ---------- 2 ----------
s.append(P("2. Literature Review: The Optimisation Space", h1))
s.append(P(
    "More context is not always better: models use evidence in the middle of long inputs less reliably [4] and are "
    "distracted by irrelevant passages [5], so the aim is the smallest set of high-signal tokens [6]. On the hardware "
    "side, Splitwise [1] and DistServe [2] separate the compute-bound prefill from the memory-bound decode, and "
    "PagedAttention [3] shows that the KV cache created by long inputs limits how many users an accelerator can "
    "serve. These works optimise the serving system; this study applies the same phase distinction to the "
    "<i>application</i>, which decides how many tokens of each kind are sent. Building on the RAG survey in [13], Table 1 organises five levers by the "
    "question each answers: how much context is needed, what is its smallest form, and how much must be said back."))
t1 = [["Lever", "How it works", "Reduces", "Expected benefit", "Risk"],
      ["T1 Adaptive retrieval", "Rerank candidates [15]; keep only passages above a threshold τ, so the number k varies and may be 0 [7, 8].", "Input (prefill, KV cache)", "Shrinks the largest input source; k = 0 gives a token-free “not found”.", "Strict τ drops needed evidence."],
      ["T2 Context compression", "Keep query-relevant sentences or summarise passages [9, 10].", "Input", "As little as 6% of tokens with minimal loss [9].", "Summaries break citation traceability."],
      ["T3 History compaction", "Recent turns verbatim, older turns summarised, used tool outputs dropped [6].", "Input", "Stops history growth; savings multiply over agent steps.", "Early user constraints lost."],
      ["T4 Output budgeting", "Short, cited answer contract; concise reasoning [11]; token cap.", "Output (decode)", "Targets the slowest, sequential phase.", "Too terse; truncation."],
      ["T5 Model cascade", "Small model first; escalate when a confidence check fails [12].", "Cost per token", "Large cost savings reported [12].", "Failed attempts paid twice."]]
s.append(P("<b>Table 1.</b> Five levers for reducing token usage. Prompt caching is excluded on purpose: it saves "
           "recomputation, not tokens, and complements every lever.", capk))
s.append(T(t1, [2.8 * cm, 5.2 * cm, 2.2 * cm, 3.9 * cm, W - 14.1 * cm]))

# ---------- 3 ----------
s.append(P("3. Methodology", h1))
s.append(P(
    "<b>Selection and rationale.</b> T1 and T4 were selected because they cover <i>one inference phase each</i>, which "
    "makes RQ2 testable; they target the largest token sources; they need no model training; and both keep source "
    "text verbatim, so every citation still points to a real passage. T2 risks traceability, T3 needs multi-turn data "
    "and T5 a calibrated confidence signal, so they form the next iteration."))
s.append(P(
    f"<b>Data and materials.</b> About 80 pages of public operational documentation ({ph('source')}) serve as the "
    "knowledge base. The test set has 40 questions with reference answers and gold passage IDs: 25 single-fact, 8 "
    f"two-passage and 7 unanswerable. Model: {ph('model name')}, temperature 0. Passages of ~250 tokens are embedded "
    "with all-MiniLM-L6-v2 [16] and reranked with a MiniLM cross-encoder [15]."))
s.append(P(
    "<b>Procedure.</b> T1 retrieves 20 candidates, reranks them and keeps up to four with score ≥ τ; if none "
    "qualifies, the agent answers “not found” <i>without calling the LLM</i>. τ is swept over six values to "
    "map the trade-off. T4 enforces an answer contract (answer first, at most three sentences, passage IDs as "
    "citations) with a 150-token cap, logging how often the cap is hit. Five variants form an ablation: <b>V0</b> "
    "baseline (top-10 whole documents, free-form answer), <b>V1</b> T1 only, <b>V2</b> T4 only, <b>V3</b> T1 + T4, "
    "and <b>VO</b> an oracle given only the gold passages, which bounds the possible saving."))
s.append(P(
    "<b>Analysis.</b> Efficiency: input and output tokens, time to first token (TTFT) and end-to-end latency (streamed, "
    "three runs). Quality: correctness judged by an LLM against reference answers (as in RAGAS [14]), with 20% checked by hand; citation "
    "precision; abstention accuracy. The headline metric, <b>TCCA</b>, divides total tokens by the number of answers "
    "that are both correct and correctly cited, so savings bought with wrong answers make it worse. The <b>exchange "
    "rate</b> is c/b from the regression latency ≈ a + b·N<sub>in</sub> + c·N<sub>out</sub>. A variant is "
    "acceptable only if correctness drops by at most three points and abstention does not drop, a margin fixed before "
    "the experiment. Variants are compared per question (McNemar’s test, bootstrap intervals), and each regression is "
    "labelled as a retrieval miss, over-strict threshold, truncation or wrong citation."))

# ---------- 4 ----------
s.append(P("4. Results", h1))
cols = ["Variant", "Input tokens", "Output tokens", "TTFT (s)", "Latency (s)", "Correct (%)", "Cited (%)", "Abstain (%)", "TCCA"]
t4 = [cols] + [[r["variant"], val(r, "input_tokens"), val(r, "output_tokens"), val(r, "ttft_s", "{:.2f}"),
                val(r, "latency_s", "{:.2f}"), val(r, "correct_pct"), val(r, "citation_precision_pct"),
                val(r, "abstention_acc_pct"), val(r, "tcca")] for r in rows]
s.append(P("<b>Table 2.</b> Results per variant (means over 40 questions). Cited = citation precision; Abstain = "
           "abstention accuracy; TCCA = tokens per correct cited answer.", capk))
s.append(T(t4, [3.4 * cm] + [(W - 3.4 * cm) / 8] * 8))
s.append(Spacer(1, 5))
s.append(KeepTogether([img("fig1_tokens_quality.png", W * 0.92),
    P("<b>Figure 1.</b> (a) Mean tokens per query: input (grey) and output (black). (b) Share of answers that are "
      "correct and correctly cited.", cap)]))
f2 = img("fig2_token_exchange_rate.png", 7.4 * cm)
side = [P("<b>Figure 2.</b> Added latency per input and per output token, from the regression over all runs.", cap),
        P(ph("Objective summary of Table 2 and Figures 1 and 2: token reduction of V1, V2 and V3 relative to V0, "
             "change in correctness, citation precision and abstention, and the measured exchange rate. Then the "
             "failure taxonomy counts for V3."), S("sb", fontSize=11.5, leading=13.6, alignment=TA_LEFT))]
lay = Table([[f2, side]], colWidths=[7.8 * cm, W - 7.8 * cm])
lay.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                         ("RIGHTPADDING", (0, 0), (0, 0), 8), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
s.append(lay)

# ---------- 5 ----------
s.append(P("5. Discussion", h1))
s.append(P(ph("Answer RQ1 to RQ3 using the results. Compare with the literature: did the oracle beat the baseline, "
              "as [4, 5] predict, and does the exchange rate match the prefill/decode characterisation in [1, 2]? "
              "Explain any unexpected result with an example from the failure taxonomy, and state what this means "
              "for designing an operational knowledge hub."), body))

# ---------- 6 ----------
s.append(P("6. Conclusion", h1))
s.append(P(ph("Main findings in two sentences.") + " Beyond the numbers, this study contributes a phase-aware way "
    "to choose token optimisations, a metric that rewards only savings that keep answers correct and cited, and a "
    "simple method to measure the relative cost of input and output tokens on any deployment. <b>Limitations:</b> "
    "40 questions from one domain, one model, API latency that includes network noise, a possibly biased LLM judge, "
    "and a threshold tuned on the evaluation set. <b>Future work:</b> history compaction with multi-turn data, a "
    "citation-gated model cascade, cache-aware prompt ordering, and profiling prefill and decode on a locally "
    "served model."))
s.append(P("<b>Use of AI tools.</b> " + ph("Which tools you used and for what; that you verified every source, line "
           "of code and result yourself."), S("ai", fontSize=11, leading=13.2)))

# ---------- References ----------
s.append(PageBreak())
s.append(P("References", h1))
refs = [
    "P. Patel <i>et al.</i>, “Splitwise: Efficient generative LLM inference using phase splitting,” in <i>Proc. ISCA</i>, 2024. arXiv:2311.18677.",
    "Y. Zhong <i>et al.</i>, “DistServe: Disaggregating prefill and decoding for goodput-optimized large language model serving,” in <i>Proc. OSDI</i>, 2024. arXiv:2401.09670.",
    "W. Kwon <i>et al.</i>, “Efficient memory management for large language model serving with PagedAttention,” in <i>Proc. SOSP</i>, 2023. arXiv:2309.06180.",
    "N. F. Liu <i>et al.</i>, “Lost in the middle: How language models use long contexts,” <i>Trans. Assoc. Comput. Linguistics</i>, vol. 12, pp. 157–173, 2024.",
    "F. Shi <i>et al.</i>, “Large language models can be easily distracted by irrelevant context,” in <i>Proc. ICML</i>, 2023. arXiv:2302.00093.",
    "Anthropic, “Effective context engineering for AI agents,” Anthropic Engineering Blog, 2025. [Online]. Available: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents",
    "S. Jeong, J. Baek, S. Cho, S. J. Hwang, and J. C. Park, “Adaptive-RAG: Learning to adapt retrieval-augmented large language models through question complexity,” in <i>Proc. NAACL</i>, 2024. arXiv:2403.14403.",
    "A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, “Self-RAG: Learning to retrieve, generate, and critique through self-reflection,” in <i>Proc. ICLR</i>, 2024. arXiv:2310.11511.",
    "F. Xu, W. Shi, and E. Choi, “RECOMP: Improving retrieval-augmented LMs with context compression and selective augmentation,” in <i>Proc. ICLR</i>, 2024. arXiv:2310.04408.",
    "H. Jiang, Q. Wu, C.-Y. Lin, Y. Yang, and L. Qiu, “LLMLingua: Compressing prompts for accelerated inference of large language models,” in <i>Proc. EMNLP</i>, 2023. arXiv:2310.05736.",
    "S. Xu, W. Xie, L. Zhao, and P. He, “Chain of draft: Thinking faster by writing less,” arXiv:2502.18600, 2025.",
    "L. Chen, M. Zaharia, and J. Zou, “FrugalGPT: How to use large language models while reducing cost and improving performance,” arXiv:2305.05176, 2023.",
    "Y. Gao <i>et al.</i>, “Retrieval-augmented generation for large language models: A survey,” arXiv:2312.10997, 2023.",
    "S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, “RAGAS: Automated evaluation of retrieval augmented generation,” in <i>Proc. EACL (System Demonstrations)</i>, 2024. arXiv:2309.15217.",
    "R. Nogueira and K. Cho, “Passage re-ranking with BERT,” arXiv:1901.04085, 2019.",
    "N. Reimers and I. Gurevych, “Sentence-BERT: Sentence embeddings using Siamese BERT-networks,” in <i>Proc. EMNLP-IJCNLP</i>, 2019. arXiv:1908.10084.",
]
for i, r in enumerate(refs, 1):
    s.append(P(f"[{i}]&nbsp;&nbsp;{r}", ref))
doc.build(s)
print("built; placeholder =", placeholder)
