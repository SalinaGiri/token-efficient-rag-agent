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
tbls = S("tbls", fontSize=9, leading=10.4, alignment=TA_LEFT)
tblsb = S("tblsb", fontName="TNR-B", fontSize=9, leading=10.4, alignment=TA_LEFT)
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

def T(rows, widths, small=False):
    hb, hn = (tblsb, tbls) if small else (tblb, tbl)
    data = [[P(c, hb) for c in rows[0]]] + [[P(c, hb if i == 0 else hn) for i, c in enumerate(r)] for r in rows[1:]]
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
if placeholder or not os.path.exists("key_numbers.json"):
    raise SystemExit("No measured results yet: run `python run.py analyze` first (writes results.csv and key_numbers.json).")

# ---------- key numbers: every number in the text is read from key_numbers.json (written by `run.py analyze`) ----------
import json
K = json.load(open("key_numbers.json"))
CORPUS = json.load(open(os.path.join("..", "data", "corpus_info.json")))
_RUNS = [json.loads(l) for l in open(os.path.join("..", "results", "runs.jsonl"), encoding="utf-8")]
N_SWEEP = sum(r["experiment"] == "sweep" for r in _RUNS)
N_MAIN = sum(r["experiment"] == "main" for r in _RUNS)
N_LLM = sum(bool(r.get("llm_called")) for r in _RUNS)
AI_USE = open("ai_use.txt", encoding="utf-8").read().strip() if os.path.exists("ai_use.txt") else ""
REPO = "https://github.com/SalinaGiri/token-efficient-rag-agent"
V, C, LAT, HW = K["variants"], K["vs_v0"], K["latency"], K["hardware"]
v0, v1, v2, v3, vo = (V[k] for k in ("V0", "V1", "V2", "V3", "VO"))
CTX, CV, J, SC = K["decode_by_context"], K["cv"], K["judge"], K["scale"]
REG3 = K["regressions"].get("V3", {})
def num(x, d=0): return f"{x:,.{d}f}"
def pts(x, d=1): return f"{x:+.{d}f}".replace("-", "−")
def neg(x, d=1): return f"{x:.{d}f}".replace("-", "−")
def red(a, b, k): return 100 * (1 - b[k] / a[k])
def ci(v): return f"95% CI {neg(C[v]['ci_lo'])} to {neg(C[v]['ci_hi'])}; McNemar p = {C[v]['p']:.2f}"
def val(r, k, fmt="{:,.0f}"): return fmt.format(float(r[k]))

s = []
# ---------- Title block ----------
s += [P("Fewer, Better Tokens", S("t", fontName="TNR-B", fontSize=17, leading=21, alignment=TA_CENTER)),
      P("A Hardware-Aware Approach to Token Efficiency in an Operational Knowledge Assistant",
        S("st", fontName="TNR-I", fontSize=12.5, leading=16, alignment=TA_CENTER, spaceAfter=4)),
      P(f"Salina Giri · Applied Computer Science, UC Leuven-Limburg (UCLL), Belgium · November 2026<br/>"
        f"Technical exercise, internship 2026-INT-298 · Code and data: {REPO}",
        S("au", fontSize=10.5, leading=13, alignment=TA_CENTER, spaceAfter=6))]
rule = Table([[""]], colWidths=[W], rowHeights=[2]); rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.6, BLACK)]))
s.append(rule)

s.append(P(
    "<b>Abstract.</b> LLM inference runs in two phases with different hardware behaviour: a parallel, compute-bound "
    "<i>prefill</i> over input tokens and a sequential, memory-bandwidth-bound <i>decode</i> that generates output "
    "tokens [1, 2]. This paper treats token efficiency as a hardware-aware design problem: it reviews five "
    "optimisation levers, selects one per phase (adaptive retrieval for input, output budgeting for output) and "
    "evaluates them in a five-variant ablation on 40 questions, seven of them unanswerable. "
    f"Adaptive retrieval cut input tokens by {red(v0, v1, 'input_tokens'):.0f}% and mean latency from "
    f"{v0['latency_s']:.1f} s to {v1['latency_s']:.1f} s without loss of correctness, and raised abstention accuracy "
    f"from {v0['abstention_acc_pct']:.0f}% to {v1['abstention_acc_pct']:.0f}%. Output budgeting cut output tokens by "
    f"{red(v0, v2, 'output_tokens'):.0f}% but cost {neg(-C['V2']['diff_points'], 0)} points of correctness. On the "
    f"laptop GPU used, one output token cost only about {LAT['exchange_rate']:.0f} input tokens of latency, so the "
    "input side dominated.", abst))

# ---------- 1 ----------
s.append(P("1. Introduction", h1))
s.append(P(
    "A knowledge assistant sends the LLM instructions, history, retrieved passages and the question. As the knowledge "
    "base grows, tokens per request rise, and with them cost, latency and energy; in agents the effect compounds at "
    "every step. Yet cutting tokens carelessly removes evidence or citations. This study asks: <b>(RQ1)</b> how far "
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
    "<i>application</i>, which decides how many tokens of each kind are sent. Building on the RAG survey in [13], "
    "Table 1 organises five levers."))
t1 = [["Lever", "How it works", "Reduces", "Expected benefit", "Risk"],
      ["T1 Adaptive retrieval", "Rerank candidates [15]; keep only passages above a threshold τ, so the number k varies and may be 0 [7, 8].", "Input (prefill, KV cache)", "Shrinks the largest input source; k = 0 gives a token-free “not found”.", "Strict τ drops needed evidence."],
      ["T2 Context compression", "Keep query-relevant sentences or summarise passages [9, 10].", "Input", "As little as 6% of tokens with minimal loss [9].", "Summaries break citation traceability."],
      ["T3 History compaction", "Recent turns verbatim, older turns summarised, used tool outputs dropped [6].", "Input", "Stops history growth; savings multiply over agent steps.", "Early user constraints lost."],
      ["T4 Output budgeting", "Short, cited answer contract; concise reasoning [11]; token cap.", "Output (decode)", "Targets the slowest, sequential phase.", "Too terse; truncation."],
      ["T5 Model cascade", "Small model first; escalate when a confidence check fails [12].", "Cost per token", "Large cost savings reported [12].", "Failed attempts paid twice."]]
s.append(P("<b>Table 1.</b> Five levers for reducing token usage. Prompt caching is excluded on purpose: it saves "
           "recomputation, not tokens, and complements every lever.", capk))
s.append(T(t1, [2.5 * cm, 5.6 * cm, 2.2 * cm, 3.9 * cm, W - 14.2 * cm], small=True))

# ---------- 3 ----------
s.append(P("3. Methodology", h1))
s.append(P(
    "<b>Selection and rationale.</b> T1 and T4 were selected because they cover <i>one inference phase each</i>, which "
    "makes RQ2 testable; they target the largest token sources; they need no model training; and both keep source "
    "text verbatim, so every citation still points to a real passage. T2 risks traceability, T3 needs multi-turn data "
    "and T5 a calibrated confidence signal, so they form the next iteration."))
s.append(P(
    "<b>Data and materials.</b> Knowledge base: the Kubernetes troubleshooting documentation (snapshot of 10 November "
    f"2026: {CORPUS['sections']} sections, {CORPUS['passages']} passages of ~250 tokens, about "
    f"{num(round(CORPUS['approx_tokens_total'], -3))} tokens in total). Test set: 40 questions with reference answers "
    "and gold passages verified against the corpus (25 single-fact, 8 two-passage, 7 unanswerable). Model: "
    "Qwen2.5-3B-Instruct (Q4_K_M) served locally by Ollama on an Apple M4 MacBook Air, temperature 0; retrieval with "
    "all-MiniLM-L6-v2 [16] and a MiniLM cross-encoder [15]. All "
    f"{num(N_SWEEP + N_MAIN)} runs ({num(N_SWEEP)} in the τ sweep, {num(N_MAIN)} in the main experiment: 40 questions × 5 "
    f"variants × {K['repeats']} repeats) were executed on this machine, {num(N_LLM)} of them with an Ollama call."))
s.append(P(
    "<b>Procedure.</b> T1 retrieves 20 candidates, reranks them and keeps up to four with score ≥ τ; if none "
    "qualifies, the agent answers “not found” <i>without calling the LLM</i>. τ was swept over six values and set to "
    f"{neg(K['tau'], 0)} (Figure 2b). T4 enforces an answer contract (answer first, at most three sentences, passage "
    "IDs as citations) with a 150-token cap. Five variants form an ablation: <b>V0</b> baseline (top-10 whole "
    "documents, free-form answer), <b>V1</b> T1 only, <b>V2</b> T4 only, <b>V3</b> T1 + T4, and <b>VO</b> an oracle "
    "given only the gold passages (with T4), which bounds the possible saving."))
s.append(P(
    "<b>Analysis.</b> Efficiency: tokens, time to first token (TTFT) and end-to-end latency (three runs, retrieval "
    "included). Quality: correctness judged by DeepSeek-chat (another model family) against reference answers, as in "
    "RAGAS [14], with 20% graded blind by hand; citation precision; abstention accuracy. <b>TCCA</b> = tokens per "
    "correct <i>and</i> correctly cited answer; <b>TPCA</b> ignores citations. The <b>exchange rate</b> = decode time "
    "per output token ÷ prefill time per input token. A variant is acceptable only if correctness drops by at most three "
    "points and abstention does not drop, a margin fixed in advance. Tests: McNemar and bootstrap intervals per "
    "question; regressions labelled by cause; τ optimism by stratified 5-fold cross-validation (20 repeats)."))

# ---------- 4 ----------
s.append(P("4. Results", h1))
cols = ["Variant", "Input tokens", "Output tokens", "TTFT (s)", "Latency (s)", "Correct (%)", "Cited (%)",
        "Abstain (%)", "TCCA", "TPCA"]
t4 = [cols] + [[r["variant"], val(r, "input_tokens"), val(r, "output_tokens"), val(r, "ttft_s", "{:.2f}"),
                val(r, "latency_s", "{:.2f}"), val(r, "correct_pct"), val(r, "citation_precision_pct"),
                val(r, "abstention_acc_pct"), val(r, "tcca"), val(r, "tpca")] for r in rows]
s.append(P("<b>Table 2.</b> Results per variant over 40 questions (tokens and latency: means over three runs; quality: "
           "first run). Cited = citation precision; Abstain = abstention accuracy; TCCA = tokens per correct cited "
           "answer; TPCA = tokens per correct answer.", capk))
s.append(T(t4, [3.7 * cm] + [(W - 3.7 * cm) / 9] * 9))
s.append(Spacer(1, 5))
s.append(KeepTogether([img("fig1_tokens_quality.png", W * 0.64),
    P("<b>Figure 1.</b> (a) Mean tokens per query: input (grey) and output (black). (b) Correct answers (light bar) "
      "and answers that are also correctly cited (dark bar).", cap)]))
s.append(P(
    f"<b>Tokens and quality.</b> T1 (V1) cut input tokens by {red(v0, v1, 'input_tokens'):.0f}% and latency from "
    f"{v0['latency_s']:.1f} s to "
    f"{v1['latency_s']:.1f} s, while correctness changed by {pts(C['V1']['diff_points'])} points ({ci('V1')}): within "
    f"the margin. T4 (V2) cut output tokens by {red(v0, v2, 'output_tokens'):.0f}% but correctness fell by "
    f"{neg(-C['V2']['diff_points'])} points ({ci('V2')}). V3 combined both ({red(v0, v3, 'input_tokens'):.0f}% fewer "
    f"input and {red(v0, v3, 'output_tokens'):.0f}% fewer output tokens, {v3['latency_s']:.1f} s), but its "
    f"correctness fell by {neg(-C['V3']['diff_points'])} points ({ci('V3')}), missing the margin. Of the "
    f"{sum(REG3.values())} questions V0 answered correctly and V3 did not, "
    f"{REG3.get('wrong answer despite evidence', 0)} had the right evidence in context but the short answer omitted a "
    "required detail. With T1, abstention accuracy rose from "
    f"{v0['abstention_acc_pct']:.0f}% to {v1['abstention_acc_pct']:.0f}%; in V3, {100 - v3['llm_calls_pct']:.0f}% of "
    "questions got “not found” without any LLM call. The baseline almost never cited a passage, which inflates its "
    f"TCCA; ignoring citations, TPCA still fell from {num(v0['tpca'])} to {num(v1['tpca'])} (V1) and "
    f"{num(v3['tpca'])} (V3)."))
s.append(KeepTogether([img("fig2_token_exchange_rate.png", W * 0.64),
    P("<b>Figure 2.</b> (a) Measured latency per input token (prefill) and per output token (decode). (b) Tokens per "
      "query against correctness for every swept τ (sweep run); the dotted line is the non-inferiority margin.", cap)]))
s.append(P(
    f"<b>Latency and hardware.</b> Prefill ran at {HW['prefill_measured_tok_s']:.0f} tokens/s and decode at "
    f"{HW['decode_measured_tok_s']:.0f} tokens/s, so one output token cost as much latency as "
    f"{LAT['exchange_rate']:.0f} input tokens. Decode reached {HW['bandwidth_utilisation_pct']:.0f}% of the memory-bandwidth ceiling "
    f"of {HW['decode_ceiling_tok_s']:.0f} tokens/s ({HW['bandwidth_gb_s']:.0f} GB/s ÷ {HW['model_gb']:.1f} GB of "
    "weights), as expected for a bandwidth-bound phase. Long prompts slowed every output token "
    f"({CTX['long']['ms_per_output_token']:.1f} vs {CTX['short']['ms_per_output_token']:.1f} ms), because each decode "
    f"step also reads the prompt’s KV cache ({HW['kv_bytes_per_token'] / 1024:.0f} KiB per token)."))
s.append(P(
    f"<b>Robustness.</b> Cross-validating τ lowered V3 correctness from {CV['V3']['in_sample_correct_pct']:.0f}% to "
    f"{CV['V3']['cv_correct_pct']:.0f}% (V1: {CV['V1']['in_sample_correct_pct']:.0f}% to "
    f"{CV['V1']['cv_correct_pct']:.0f}%), so tuning on the test set is optimistic by up to "
    f"{max(CV['V3']['optimism_points'], CV['V1']['optimism_points']):.0f} points. The judge agreed with the blind "
    f"manual grades on {J['agree']} of {J['n']} answers (Cohen’s κ = {J['kappa']:.2f}); both disagreements were "
    "multi-part answers missing a step."))

# ---------- 5 ----------
s.append(P("5. Discussion", h1))
s.append(P(
    "<b>RQ1.</b> Input tokens can be cut by an order of magnitude without losing correctness: dropping low-scoring "
    "passages helped rather than hurt, in line with [4, 5]. Output is harder: the fixed three-sentence contract left out "
    f"secondary facts, so T4 failed the margin; the oracle, which uses the same contract, scored only "
    f"{vo['correct_pct']:.0f}%, pointing to the contract, not retrieval, as the limit. <b>RQ2.</b> The two token types cost differently, but the ratio depends on "
    "the hardware: on this laptop GPU prefill is slow, so the baseline prompt dominated latency (first token after "
    f"{v0['ttft_s']:.1f} of {v0['latency_s']:.1f} s) and T1 saved far more time than T4. Where prefill is much faster "
    "relative to decode, as on data-centre accelerators [1, 2], output reduction gains weight, so the exchange rate "
    "should be measured per deployment. <b>RQ3.</b> Yes: abstention accuracy rose from "
    f"{v0['abstention_acc_pct']:.0f}% to {v1['abstention_acc_pct']:.0f}%. For a knowledge hub this suggests adaptive "
    "retrieval by default and an output budget that adapts to the question. "
    f"At {num(SC['queries_per_day'])} queries a day, V3’s measured "
    f"savings would amount to about {SC['input_tokens_saved_per_day'] / 1e6:,.0f} million input tokens and "
    f"{SC['machine_hours_saved_per_day']:,.0f} machine-hours per day on this hardware"
    + " (a projection from measured means" + (f"; about {SC['api_cost_saved_per_day']:,.0f} USD at DeepSeek-Flash "
       "peak list prices" if "api_cost_saved_per_day" in SC else "") + ")."))

# ---------- 6 ----------
s.append(P("6. Conclusion", h1))
s.append(P(
    f"Adaptive retrieval is the clear win: {red(v0, v1, 'input_tokens'):.0f}% fewer input tokens, "
    f"{v0['latency_s'] / v1['latency_s']:.0f} times lower latency and better abstention at equal correctness. A fixed "
    "output budget saves decode time but costs completeness. <b>Limitations:</b> 40 "
    "questions from one domain; one 3B model on one fanless laptop (cooling breaks between runs); a judge slightly "
    "lenient on multi-part answers; τ tuned on the test set. <b>Future work:</b> question-adaptive output budgets, "
    "history compaction, a citation-gated cascade, and the exchange rate on a server GPU."))
s.append(P("<b>Use of AI tools.</b> " + (AI_USE or ph("Which tools you used and for what; that you verified every "
           "source, line of code and result yourself.")), S("ai", fontSize=11, leading=13.2)))


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
print("built; pages =", doc.page, "(last page = references)")
