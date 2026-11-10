"""Build the research paper PDF.  Run make_figures.py first.
Text in grey boxes [like this] is a placeholder: replace it with your own content."""
import csv
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, Image, KeepTogether, NextPageTemplate)
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

BLACK = colors.black
PH = "#E4E4E4"

def S(name, **kw):
    d = dict(fontName="TNR", fontSize=12, leading=16.5, textColor=BLACK, alignment=TA_JUSTIFY)
    d.update(kw)
    return ParagraphStyle(name, **d)

body = S("body", spaceAfter=7)
first = body
bul = S("bul", leftIndent=16, bulletIndent=3, spaceAfter=4)
h1 = S("h1", fontName="TNR-B", fontSize=13, leading=17, alignment=TA_LEFT, spaceBefore=12, spaceAfter=6, keepWithNext=1)
h2 = S("h2", fontName="TNR-BI", fontSize=12, leading=16, alignment=TA_LEFT, spaceBefore=6, spaceAfter=3, keepWithNext=1)
tbl = S("tbl", fontSize=10.5, leading=13, alignment=TA_LEFT)
tblb = S("tblb", fontName="TNR-B", fontSize=10.5, leading=13, alignment=TA_LEFT)
cap = S("cap", fontSize=10.5, leading=13.5, alignment=TA_LEFT, spaceBefore=4, spaceAfter=10)
capk = S("capk", fontSize=10.5, leading=13.5, alignment=TA_LEFT, spaceAfter=4, keepWithNext=1)
ref = S("ref", fontSize=11, leading=14.5, alignment=TA_LEFT, leftIndent=26, firstLineIndent=-26, spaceAfter=5)
abst = S("abst", fontSize=12, leading=16.5, leftIndent=0.8 * cm, rightIndent=0.8 * cm, spaceAfter=6)
c_title = S("ct", fontName="TNR-B", fontSize=20, leading=26, alignment=TA_CENTER)
c_sub = S("cs", fontName="TNR-I", fontSize=14, leading=19, alignment=TA_CENTER)
c_txt = S("cx", fontSize=12, leading=17, alignment=TA_CENTER)

def P(t, st=body): return Paragraph(t, st)
def B(t): return Paragraph(t, bul, bulletText="•")
def ph(t): return f'<font backColor="{PH}"><i>[{t}]</i></font>'

PAGE_W, PAGE_H = A4
M = 2.54 * cm
W = PAGE_W - 2 * M

def booktabs(data, widths, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEABOVE", (0, 0), (-1, 0), 1.0, BLACK),
          ("LINEBELOW", (0, -1), (-1, -1), 1.0, BLACK),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st.append(("LINEBELOW", (0, 0), (-1, 0), 0.6, BLACK))
    t.setStyle(TableStyle(st))
    return t

def T(rows, widths, bold_first_col=True):
    data = [[P(c, tblb) for c in rows[0]]]
    for r in rows[1:]:
        data.append([P(c, tblb if (bold_first_col and i == 0) else tbl) for i, c in enumerate(r)])
    return booktabs(data, widths)

def figure(path, width, caption):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    img = Image(path, width=width, height=width * ih / iw)
    img.hAlign = "CENTER"
    return KeepTogether([img, P(caption, cap)])

def footer(c, doc):
    c.saveState(); c.setFont("TNR", 10.5)
    c.drawCentredString(PAGE_W / 2, 1.4 * cm, str(doc.page))
    c.restoreState()

doc = BaseDocTemplate("Fewer_Better_Tokens_Research_Paper.pdf", pagesize=A4,
                      leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=M,
                      title="Fewer, Better Tokens: A Hardware-Aware Approach to Token Efficiency in an Operational Knowledge Assistant",
                      author="Salina Giri")
fr = Frame(M, M, W, PAGE_H - 2 * M, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="cover", frames=[fr]),
                      PageTemplate(id="main", frames=[fr], onPage=footer)])

# ---------- results data ----------
rows = list(csv.DictReader(open("results.csv", newline="")))
placeholder = any(r["placeholder"].strip().lower() == "yes" for r in rows)
def val(r, k, fmt="{:,.0f}"):
    return ph(" ") if placeholder else fmt.format(float(r[k]))

s = []
# ================= TITLE PAGE =================
s += [Spacer(1, 4.2 * cm),
      P("Fewer, Better Tokens", c_title), Spacer(1, 6),
      P("A Hardware-Aware Approach to Token Efficiency<br/>in an Operational Knowledge Assistant", c_sub),
      Spacer(1, 2.4 * cm),
      P("<b>Salina Giri</b>", c_txt),
      P("Bachelor of Applied Computer Science", c_txt),
      P("UC Leuven-Limburg (UCLL), Leuven, Belgium", c_txt),
      Spacer(1, 1.6 * cm),
      P("Technical exercise submitted for internship 2026-INT-298<br/>"
        "<i>Token-Efficient AI-Agent Design for an Operational Knowledge Hub</i>", c_txt),
      Spacer(1, 1.6 * cm),
      P("November 2026", c_txt),
      Spacer(1, 4),
      P(f"Code and data: {ph('GitHub repository link')}", c_txt),
      NextPageTemplate("main"), PageBreak()]

# ================= ABSTRACT =================
s.append(P("Abstract", S("abh", fontName="TNR-B", fontSize=13, leading=17, alignment=TA_CENTER, spaceAfter=8)))
s.append(P(
    "Large language model (LLM) knowledge assistants become slow and expensive as their context fills with system "
    "instructions, conversation history and retrieved documents. Most token-reduction work treats every token as "
    "equal, yet LLM inference runs in two phases with different hardware behaviour: a parallel, compute-bound "
    "<i>prefill</i> over the input and a sequential, memory-bandwidth-bound <i>decode</i> that generates the output. "
    "This paper treats token efficiency as a hardware-aware design problem. It reviews five optimisation levers and "
    "selects one for each inference phase: adaptive, precision-first retrieval to reduce input tokens, and output "
    "budgeting to reduce output tokens. A proof of concept compares a baseline retrieval-augmented agent with "
    "token-optimised variants in a five-variant ablation on 40 questions over an operational documentation corpus, "
    "including seven questions that cannot be answered from the corpus. Quality is measured by answer correctness, "
    "citation precision and abstention accuracy; efficiency by token counts, time to first token and end-to-end "
    "latency. Two evaluation ideas are introduced: <i>tokens per correct cited answer</i> (TCCA), which penalises "
    "savings bought with wrong or unsupported answers, and a measured latency <i>exchange rate</i> between output and "
    "input tokens. " + ph("Key findings in two sentences: the token reduction and change in correctness of the "
    "optimised agent, and the measured exchange rate.") + " " +
    ph("One concluding sentence on what this means for designing a token-efficient knowledge assistant."), abst))
s.append(P("<b>Keywords:</b> large language models; retrieval-augmented generation; token efficiency; LLM inference; "
           "prefill and decode; evaluation", abst))

# ================= 1 INTRODUCTION =================
s.append(P("1. Introduction", h1))
s.append(P(
    "Operational knowledge assistants answer staff questions using an organisation’s internal documentation. A "
    "typical request to the underlying LLM combines system instructions, conversation history, retrieved passages, "
    "the user’s question and the generated response. As the knowledge base and the conversation grow, so does the "
    "number of tokens per request, and with it the cost, the latency and the energy used to serve each answer. In "
    "agentic systems the effect compounds, because the context is sent again at every reasoning step and tool call."))
s.append(P(
    "Reducing tokens is not automatically beneficial. Removing the wrong passage produces a wrong answer, and a "
    "shorter response may drop the citation that makes the answer verifiable. The practical problem is therefore to "
    "reduce token usage <i>without</i> reducing the correctness, traceability and honesty of the answers. A second, "
    "less discussed gap is that token savings are usually counted as if every token had the same cost, although input "
    "and output tokens are processed by the hardware in very different ways."))
s.append(P("This study addresses three research questions:", body))
s.append(B("<b>RQ1.</b> How far can input and output tokens be reduced in a retrieval-augmented knowledge assistant "
           "while keeping correctness within a pre-defined margin of the baseline?"))
s.append(B("<b>RQ2.</b> Do input and output tokens have measurably different latency costs, and what is the "
           "exchange rate between them?"))
s.append(B("<b>RQ3.</b> Does adaptive retrieval improve reliability, measured as correct abstention on "
           "unanswerable questions?"))
s.append(P(
    "Section 2 reviews the literature on long-context behaviour, inference hardware and token-reduction techniques. "
    "Section 3 describes the experimental design, Section 4 reports the results, Section 5 interprets them, and "
    "Section 6 concludes with limitations and future work."))

# ================= 2 LITERATURE REVIEW =================
s.append(P("2. Literature Review", h1))
s.append(P("2.1 Long context is costly and not always helpful", h2))
s.append(P(
    "Longer context does not guarantee better answers. Liu et al. [4] show that models use information at the start "
    "and end of their input most reliably, and that accuracy drops when the relevant passage sits in the middle of a "
    "long context. Shi et al. [5] show that irrelevant context can actively distract a model from the correct answer. "
    "Anthropic’s guidance on context engineering [6] draws the practical conclusion: the goal is the smallest set of "
    "high-signal tokens that achieves the desired outcome. Together these results suggest that a well-chosen shorter "
    "context can improve quality as well as cost, which this study tests directly through an oracle condition."))
s.append(P("2.2 How inference hardware processes tokens", h2))
s.append(P(
    "Systems research separates LLM inference into two phases. In the prompt or prefill phase, all input tokens pass "
    "through the model in parallel; this phase is compute-intensive and determines the time to first token. In the "
    "token-generation or decode phase, output tokens are produced one forward pass at a time, which makes the phase "
    "memory-bandwidth-bound [1, 2]. Splitwise [1] and DistServe [2] exploit this difference by running the two phases "
    "on separate hardware, and PagedAttention [3] shows that the key-value (KV) cache created by long inputs is a "
    "major limit on how many requests one accelerator can serve. These works optimise the serving system; the "
    "application side, which decides how many tokens of each kind to send, has received less attention. This study "
    "uses the phase distinction as a design principle at the application level."))
s.append(P("2.3 Techniques for reducing token usage", h2))
s.append(P(
    "Building on the survey of retrieval-augmented generation by Gao et al. [13], Table 1 organises the literature into five levers, grouped by the question each answers for a request: how much "
    "context is needed, what is its smallest form, and how much must be said back. Adaptive retrieval methods such as "
    "Adaptive-RAG [7] and Self-RAG [8] adjust retrieval to the question, but both rely on a trained classifier or "
    "model, which adds engineering cost. Compression methods reach large reduction ratios: RECOMP [9] reports "
    "summaries as small as 6% of the original documents with minimal loss, and LLMLingua [10] up to 20× prompt "
    "compression. Their weakness for an operational setting is traceability: an abstractive summary is no longer the "
    "source text that a citation should point to. Chain of Draft [11] shortens reasoning output sharply, but it was "
    "evaluated on reasoning benchmarks rather than knowledge question answering. FrugalGPT [12] lowers cost through "
    "model cascades, but changes the price per token rather than the number of tokens."))

t1 = [["Lever", "Mechanism", "Reduces", "Main risk"],
      ["T1 Adaptive retrieval", "Rerank candidates [15]; keep only passages above a relevance threshold τ; the number of passages k varies and may be 0 [7, 8].", "Input (prefill, KV cache)", "Needed evidence dropped if τ is too strict"],
      ["T2 Context compression", "Keep only query-relevant sentences, or summarise retrieved passages [9, 10].", "Input", "Lost qualifiers; citations no longer match source"],
      ["T3 History compaction", "Keep recent turns verbatim; summarise older turns; drop used tool outputs [6].", "Input", "Early user constraints forgotten"],
      ["T4 Output budgeting", "Answer contract (short, answer first, cited); concise reasoning [11]; token cap.", "Output (decode)", "Too terse for procedures; truncation"],
      ["T5 Model cascade", "Small model first; escalate only when a confidence check fails [12].", "Cost per token", "Failed attempts paid twice"]]
s.append(P("<b>Table 1.</b> Five levers for reducing token usage in an LLM knowledge assistant.", capk))
s.append(T(t1, [3.2 * cm, 6.3 * cm, 2.6 * cm, W - 12.1 * cm]))
s.append(Spacer(1, 8))
s.append(P(
    "Prompt caching is deliberately excluded from Table 1. It reuses computation for a repeated prompt prefix and "
    "lowers cost and latency, but the model still processes every token, so it is an infrastructure saving rather "
    "than a token reduction. It is complementary to all five levers."))
s.append(P("2.4 Research gap and contribution", h2))
s.append(P(
    "Two gaps emerge. First, most techniques are evaluated on public benchmarks by answer accuracy alone, while an "
    "operational knowledge hub also depends on correct citations and on the assistant declining when the answer is "
    "not in the documentation. Evaluation frameworks such as RAGAS [14] address some of these dimensions but not "
    "their relation to token cost. Second, token savings are almost always reported as raw counts, ignoring the "
    "phase-specific cost described in Section 2.2. This study contributes (i) a phase-aware selection of techniques, "
    "one per inference phase; (ii) the TCCA metric, which ties efficiency to correct, cited answers; (iii) a measured "
    "exchange rate between output and input tokens; and (iv) abstention without an LLM call when no passage is "
    "relevant enough."))

# ================= 3 METHODOLOGY =================
s.append(P("3. Methodology", h1))
s.append(P("3.1 Research design and rationale", h2))
s.append(P(
    "The study uses a controlled, paired ablation: every variant answers the same questions with the same model, so "
    "differences can be attributed to the technique. Two techniques from Table 1 were selected. T1 targets the "
    "prefill phase and T4 the decode phase, which allows RQ2 to be tested directly. Both target the largest token "
    "sources (retrieved passages for input, generated text for output), need no model training, and keep source text "
    "verbatim, so every citation still points to a real passage. T2 was postponed because it endangers traceability, "
    "T3 because it requires multi-turn test data, and T5 because it requires a calibrated confidence signal. Table 2 "
    "lists the five variants."))
t2 = [["Variant", "Retrieval", "Output", "Purpose"],
      ["V0 Baseline", "Top-10 whole documents", "Free-form", "Typical naive RAG agent"],
      ["V1", "T1 adaptive retrieval", "Free-form", "Isolates the input-side saving"],
      ["V2", "Top-10 whole documents", "T4 output budget", "Isolates the output-side saving"],
      ["V3 Optimised", "T1 adaptive retrieval", "T4 output budget", "Combined optimised agent"],
      ["VO Oracle", "Gold passages only", "T4 output budget", "Upper bound on achievable saving"]]
s.append(P("<b>Table 2.</b> Experimental variants.", capk))
s.append(T(t2, [3.0 * cm, 4.4 * cm, 3.4 * cm, W - 10.8 * cm]))
s.append(Spacer(1, 8))

s.append(P("3.2 Data: knowledge base and test set", h2))
s.append(P(
    f"The knowledge base consists of approximately 80 pages of public operational documentation ({ph('name the source and licence')}), "
    "chosen to resemble an internal knowledge hub of runbooks, configuration guides and troubleshooting notes. The "
    "test set contains 40 questions written from the documentation, each with a reference answer and the IDs of the "
    "passages that support it: 25 single-fact questions, 8 questions that require combining two passages, and 7 "
    "questions that are deliberately unanswerable from the corpus. The unanswerable questions measure whether the "
    "assistant declines rather than inventing an answer."))

s.append(P("3.3 Materials and instruments", h2))
s.append(B(f"<b>Language model:</b> {ph('model name and version')}, temperature 0, accessed via {ph('API or local runtime')}."))
s.append(B("<b>Retrieval:</b> passages of about 250 tokens that keep their section titles; embeddings from "
           "all-MiniLM-L6-v2 [16]; reranking with the cross-encoder ms-marco-MiniLM-L-6-v2 [15]."))
s.append(B("<b>Token counts</b> from the usage fields returned by the model provider; <b>latency</b> measured with "
           "streaming, recording time to first token (TTFT) and end-to-end time."))
s.append(B(f"<b>Software:</b> Python {ph('version')} with {ph('main libraries')}; all code and data in the linked repository."))

s.append(P("3.4 Procedure", h2))
s.append(P(
    "In T1, the agent retrieves the 20 most similar passages, reranks them, and keeps those with a score of at least "
    "τ, up to a maximum of four. If no passage reaches τ, the agent returns a fixed “not found in the "
    "documentation” response without calling the LLM. Rather than tuning a single value, τ is swept over six "
    "settings to describe the full trade-off between tokens and quality. In T4, the system prompt defines an answer "
    "contract (answer first, at most three sentences, passage IDs as citations) with one example, and a cap of 150 "
    "output tokens acts as a safety limit; the share of answers that reach the cap is logged so that truncation cannot "
    "hide in averages. Each variant answers all 40 questions; latency measurements are repeated three times and "
    "averaged."))

s.append(P("3.5 Data analysis", h2))
t3 = [["Dimension", "Measure"],
      ["Efficiency", "Input and output tokens per query; TTFT; end-to-end latency; cost per query."],
      ["Quality", "Answer correctness against reference answers, judged by an LLM with 20% of judgements verified by hand; citation precision (the cited passage supports the claim)."],
      ["Reliability", "Abstention accuracy on unanswerable questions; false-abstention rate on answerable ones."],
      ["TCCA", "Total tokens divided by the number of answers that are both correct and correctly cited."],
      ["Exchange rate", "Coefficients of the regression latency ≈ a + b·N<sub>in</sub> + c·N<sub>out</sub>; the ratio c/b gives how many input tokens one output token costs in time."]]
s.append(P("<b>Table 3.</b> Evaluation measures.", capk))
s.append(T(t3, [3.0 * cm, W - 3.0 * cm]))
s.append(Spacer(1, 8))
s.append(P(
    "An optimised variant is considered acceptable only if correctness drops by at most three percentage points and "
    "abstention accuracy does not drop. This margin was fixed before the experiment to avoid explaining away a poor "
    "result afterwards. Because the test set is small, variants are compared per question with McNemar’s test and "
    "bootstrap confidence intervals rather than by averages alone. Every answer that is correct in V0 but wrong in an "
    "optimised variant is labelled as a retrieval miss, an over-strict threshold, a truncated answer or a wrong "
    "citation."))

# ================= 4 RESULTS =================
s.append(P("4. Results", h1))
s.append(P(ph("Describe the results objectively, without interpretation: the token counts of each variant compared "
              "with V0, the correctness and citation precision, the abstention accuracy, and the TCCA. Refer to "
              "Table 4 and Figures 1 and 2."), body))
cols = ["Variant", "Input tokens", "Output tokens", "TTFT (s)", "Latency (s)", "Correct (%)", "Cited (%)", "Abstain (%)", "TCCA"]
t4 = [cols]
for r in rows:
    t4.append([r["variant"], val(r, "input_tokens"), val(r, "output_tokens"), val(r, "ttft_s", "{:.2f}"),
               val(r, "latency_s", "{:.2f}"), val(r, "correct_pct"), val(r, "citation_precision_pct"),
               val(r, "abstention_acc_pct"), val(r, "tcca")])
s.append(P("<b>Table 4.</b> Results per variant (means over 40 questions; latency averaged over three runs). Cited = citation precision; Abstain = abstention accuracy on unanswerable questions; TCCA = tokens per correct cited answer.", capk))
s.append(T(t4, [3.3 * cm] + [(W - 3.3 * cm) / 8] * 8))
s.append(Spacer(1, 10))
s.append(figure("fig1_tokens_quality.png", W,
    "<b>Figure 1.</b> (a) Mean tokens per query, split into input (grey) and output (black) tokens. "
    "(b) Share of answers that are both correct and correctly cited."))
s.append(figure("fig2_token_exchange_rate.png", W * 0.66,
    "<b>Figure 2.</b> Added latency per input token and per output token, estimated by linear regression over all "
    "runs. The ratio shows how many input tokens one output token costs in time."))
s.append(P(ph("Report the failure taxonomy: how many regressions fell into each category for V3, and the share of "
              "answers that reached the output cap."), body))

# ================= 5 DISCUSSION =================
s.append(P("5. Discussion", h1))
s.append(P("5.1 Interpretation of the research questions", h2))
s.append(P(ph("RQ1: did the optimised agent stay within the 3-point margin, and which technique contributed most to "
              "the saving? RQ2: does the measured exchange rate confirm that output tokens cost more time than input "
              "tokens, and by how much? RQ3: did adaptive retrieval improve abstention on unanswerable questions?"), body))
s.append(P("5.2 Comparison with existing literature", h2))
s.append(P(ph("Compare with Section 2. For example: did the oracle condition outperform the baseline, as Liu et al. [4] "
              "and Shi et al. [5] would predict? Is the exchange rate consistent with the prefill and decode "
              "characterisation in [1, 2]?"), body))
s.append(P("5.3 Unexpected results", h2))
s.append(P(ph("Describe anything that went differently from expectation and a plausible explanation, supported by "
              "examples from the failure taxonomy."), body))
s.append(P("5.4 Implications", h2))
s.append(P(ph("What the results mean for designing a token-efficient operational knowledge hub: which technique to "
              "deploy first, how to set the threshold, and why output length deserves as much attention as context "
              "length when latency matters."), body))

# ================= 6 CONCLUSION =================
s.append(P("6. Conclusion", h1))
s.append(P(ph("Summarise the main findings in two or three sentences.") + " "
    "Beyond the specific numbers, this study contributes a phase-aware way of choosing token optimisations, a "
    "metric that only rewards savings that preserve correct and cited answers, and a simple method to measure the "
    "relative latency cost of input and output tokens on any deployment."))
s.append(P(
    "<b>Limitations.</b> The test set is small (40 questions) and drawn from one documentation domain, so the results "
    "indicate trends rather than general effects. Only one model was evaluated. Latency measured through an API "
    "includes network and queueing noise, and the LLM judge may be biased, which is why a share of its judgements was "
    "checked by hand. The relevance threshold was tuned on the same questions it was evaluated on."))
s.append(P(
    "<b>Future work.</b> Next steps are to add history compaction (T3) with multi-turn test conversations, to test a "
    "two-model cascade (T5) gated by citation checks, to measure the effect of cache-aware prompt ordering, and to "
    "repeat the exchange-rate measurement on a locally served model, where prefill and decode can be profiled "
    "directly on the hardware."))
s.append(P("<b>Use of AI tools.</b> " + ph("State honestly which AI tools you used and for what (for example "
           "literature search, structuring, wording or code assistance), and that you checked every source, line of "
           "code and result yourself."), body))

# ================= REFERENCES =================
s.append(P("References", h1))
refs = [
    "P. Patel, E. Choukse, C. Zhang, A. Shah, Í. Goiri, S. Maleki, and R. Bianchini, “Splitwise: Efficient generative LLM inference using phase splitting,” in <i>Proc. ISCA</i>, 2024. arXiv:2311.18677.",
    "Y. Zhong, S. Liu, J. Chen, J. Hu, Y. Zhu, X. Liu, X. Jin, and H. Zhang, “DistServe: Disaggregating prefill and decoding for goodput-optimized large language model serving,” in <i>Proc. OSDI</i>, 2024. arXiv:2401.09670.",
    "W. Kwon, Z. Li, S. Zhuang, Y. Sheng, L. Zheng, C. H. Yu, J. E. Gonzalez, H. Zhang, and I. Stoica, “Efficient memory management for large language model serving with PagedAttention,” in <i>Proc. SOSP</i>, 2023. arXiv:2309.06180.",
    "N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni, and P. Liang, “Lost in the middle: How language models use long contexts,” <i>Trans. Assoc. Comput. Linguistics</i>, vol. 12, pp. 157–173, 2024.",
    "F. Shi, X. Chen, K. Misra, N. Scales, D. Dohan, E. H. Chi, N. Schärli, and D. Zhou, “Large language models can be easily distracted by irrelevant context,” in <i>Proc. ICML</i>, 2023. arXiv:2302.00093.",
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
