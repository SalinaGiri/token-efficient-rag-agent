# Statistics

Latency per input token (prefill): 3.362 ms
Latency per output token (decode): 27.00 ms
Exchange rate: 1 output token = 8 input tokens in latency
Regression on LLM wall time: a = -644.4 ms, b = 3.5710 ms/input token, c = 27.29 ms/output token, R^2 = 0.969 (n = 543)

V1 vs V0: correctness +5.0 points (95% bootstrap CI -10.0 to +17.5); only V0 correct: 3, only V1 correct: 5, McNemar exact p = 0.727; non-inferiority rule: PASS
V2 vs V0: correctness -17.5 points (95% bootstrap CI -32.5 to -5.0); only V0 correct: 8, only V2 correct: 1, McNemar exact p = 0.039; non-inferiority rule: FAIL
V3 vs V0: correctness -10.0 points (95% bootstrap CI -25.0 to +5.0); only V0 correct: 7, only V3 correct: 3, McNemar exact p = 0.344; non-inferiority rule: FAIL
VO vs V0: correctness -5.0 points (95% bootstrap CI -20.0 to +10.0); only V0 correct: 6, only VO correct: 4, McNemar exact p = 0.754; non-inferiority rule: FAIL

Judge agreement with your manual grades: 31/33 (94%)
Cohen's kappa (judge vs manual, n = 33): 0.84

Cross-validated TAU for V3 (5-fold x 20, sweep data): in-sample TAU 0.0 gives 80.0% correct, held-out 72.8% (optimism +7.2 points); abstention 100% vs 87%; TCCA 921 vs 974; TAU picks per fold: {0.0: 60, 1.0: 33, 2.0: 6, 2.5: 1}

Cross-validated TAU for V1 (5-fold x 20, sweep data): in-sample TAU 1.0 gives 85.0% correct, held-out 82.4% (optimism +2.6 points); abstention 100% vs 100%; TCCA 1465 vs 1671; TAU picks per fold: {-1.5: 10, 0.0: 21, 1.0: 69}

Hardware (Apple M4 (MacBook), 120 GB/s, model file 2.10 GB): decode ceiling 57 tok/s, measured 37.0 tok/s (65% of the bandwidth limit); prefill measured 297 tok/s
KV cache: 36 KiB per token, 0.24 GB for a mean long prompt; decode ceiling with it 51 tok/s
Decode with short prompts (mean 644 tokens, n = 303): 24.3 ms per output token
Decode with long prompts (mean 6522 tokens, n = 240): 29.0 ms per output token

Scale projection, V3 vs V0 at 100,000 queries/day: 583M input and 9.7M output tokens saved per day; 22.94 s faster per query, 637 machine-hours per day on this hardware; API cost saved 186.55 USD/day
