# Threat Model and Security (paper section, draft)

> Draft written from the measured results in `results/`. Items marked **[TODO]** need numbers from your machine.
> Verify every citation against the PDF before submission.

## 1. Threat model
AgentOS lets language-model agents read files, run commands and use the network. The adversary is an
**indirect prompt injector**: they never talk to the system, but they control some content an agent will read
(a document, a log line, a saved web page, or the output of a tool). The injected text tries to make the agent
perform an action the user never asked for. We assume the worst case, that **the model obeys the injection**,
so safety must not depend on model robustness. Assets are user files (integrity), secrets (confidentiality) and
the host (no arbitrary execution or exfiltration). Trusted: the user's direct request, the policy file, and system
code. Untrusted: model output, and any text from files, logs, web pages or tools. Out of scope: kernel and sandbox
exploits, a malicious user, side channels, and attacks that stay inside an agent's permissions and only change the
answer text (Section 6).

## 2. Design: the model proposes, the OS decides
The LLM can only *propose* tool calls. Every call goes through a policy engine before it touches the system:
1. **Deny by default.** Unknown agents or actions are denied. A per-agent capability table (`fs.read`, `fs.write`,
   `fs.delete`, `shell.exec`, `net`) grants the minimum: GeneralAgent none, SecurityAgent read-only, FileAgent files
   plus an allowlisted shell. This follows least privilege [Saltzer & Schroeder 1975].
2. **Path control.** Paths are resolved with `realpath` before checking, so `../` and symlinks cannot leave the
   workspace; a `secrets/` folder is protected even inside it.
3. **Command control.** Commands are argv lists matched against an allowlist, never shell strings; path-like
   arguments, including values hidden in options such as `--opt=/path`, are checked like file targets.
4. **Taint tracking.** Anything read from a file or tool output marks the task *tainted*. After that, deleting,
   overwriting an existing file, running a command, or using the network requires explicit user approval.
5. **Sandbox.** Commands run under bubblewrap with no network, read-only system directories and one writable workspace.
6. **Audit log.** Every decision is written as one JSONL line (task, agent, action, target, decision, reason, layer).

A read-only **SecurityAgent** scans content for injection patterns (including base64-hidden ones). It is advisory:
enforcement never depends on it.

## 3. Evaluation method
**Attack suite.** 22 attacks in 8 categories, each a JSON file with a code-checkable success condition (for example
"data.txt no longer exists" or "the secret appears in an outgoing request"): malicious file content (4), poisoned tool
output (3), hidden web text (3), path traversal and symlinks (3), exfiltration (3), privilege escalation (2),
obfuscated or multi-step (2), and answer manipulation (2). 20 attacks target an unsafe *action*; 2 only manipulate the
answer text. **Benign suite.** 16 ordinary tasks that must keep working.
**Models.** A scripted *compromised* LLM that obeys every instruction it can parse (worst case, deterministic), and
the real Qwen2.5-1.5B through Ollama **[TODO: fill the real-model table from `make qwen`]**.
**Configurations (ablation).** `off` (no enforcement), `caps` (capabilities + path + command rules), `caps+taint`
(adds taint rules), and `caps+taint+sandbox`. All runs use a fresh temporary workspace, so the attacks are safe to run.
**Validity.** With enforcement off, all 20 action-level attacks succeed, so none of them is ineffective.

## 4. Results
Attacks that succeeded (lower is better), scripted compromised LLM:

| category | off | caps | caps+taint |
|---|---|---|---|
| malicious file | 4/4 | 4/4 | 0/4 |
| poisoned tool output | 3/3 | 0/3 | 0/3 |
| hidden web text | 3/3 | 3/3 | 0/3 |
| path traversal / symlink | 3/3 | 0/3 | 0/3 |
| exfiltration | 3/3 | 0/3 | 0/3 |
| privilege escalation | 2/2 | 0/2 | 0/2 |
| obfuscated / multi-step | 2/2 | 2/2 | 0/2 |
| **all action-level** | **20/20** | **9/20** | **0/20** |
| answer manipulation | 2/2 | 2/2 | 2/2 |

**Headline:** 20 of 20 action-level attacks succeed without enforcement and 0 of 20 with it. Capabilities alone
stop 11 of 20 (path, command and network rules); the 9 that remain act *inside* FileAgent's permissions (deleting or
overwriting a workspace file after reading a poisoned input), and the taint rule is what stops them.

**Benign tasks.** All 16 pass with `off` and `caps`. With `caps+taint`, 12 pass untouched and 4 (read-then-delete,
two commands in a row, read-then-grep, read-then-overwrite) ask for approval; all 16 pass once approved. This is the
price of conservative task-level taint.

**Overhead.** A policy check, including writing the audit line, takes 0.051 ms on average (p95 0.089 ms; 20,000
calls), negligible against LLM inference time.

**Bugs the suite found.** Our first policy version allowed an injected overwrite after untrusted input and a path
hidden in a command option (`wc --files0-from=/etc/passwd`); they let 2/20 and 10/20 attacks through in the
`caps+taint` and `caps` configurations. Both were fixed, and the numbers above are for the fixed policy.
**Sandbox.** **[TODO: run `python sandbox_check.py` on a machine with bubblewrap and report whether the sandbox
contained the option-path bug when the policy was deliberately left unfixed.]**
**Detection.** The SecurityAgent scanner flagged 14 of 22 attack payloads and 1 of 16 benign inputs.

## 5. Discussion
Layers are complementary: path and command rules stop out-of-bounds access; capabilities stop privilege escalation;
only the taint rule stops attacks that stay within granted permissions. Under the full configuration taint often
fires first, so per-layer attribution should be read from the `caps` column rather than the layer counts.

## 6. Limitations
- **Answer manipulation is not prevented.** A poisoned file can change what the agent *says* using only `fs.read`;
  both such attacks succeed in every configuration.
- The suite has 22 attacks written by the authors, with knowledge of the defence. "0/20" describes this suite, not
  general security. The scripted model is a worst case, not a measure of how often real models comply.
- Task-level taint is coarse (4/16 benign tasks need approval). Finer data-flow tracking could reduce this.
- We do not defend against kernel or bubblewrap vulnerabilities, a malicious user, or side channels.
- Model-based evaluation used a 1.5B model on CPU; larger models may behave differently.

## 7. Related work
Indirect prompt injection was shown against real LLM-integrated applications by Greshake et al. (2023), building on
earlier work on goal hijacking by Perez and Ribeiro (2022). Benchmarks such as InjecAgent (Zhan et al., 2024) and
AgentDojo (Debenedetti et al., 2024) measure how often tool-using agents follow injected instructions. Debenedetti
et al. (2025) propose CaMeL, which separates control flow from untrusted data and enforces capabilities on data
flow; our taint rule is a much coarser, task-level version of the same principle. AIOS (Mei et al., 2024) treats
LLM agents as operating-system processes with scheduling and access control; our work adds an explicit evaluation of
capability enforcement against injection. Our design follows the principle of least privilege (Saltzer and
Schroeder, 1975) and uses bubblewrap (containers/bubblewrap) for unprivileged sandboxing.

## References (arXiv ids checked against the arXiv pages)
1. K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, M. Fritz. *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* arXiv:2302.12173, 2023.
2. F. Perez, I. Ribeiro. *Ignore Previous Prompt: Attack Techniques For Language Models.* arXiv:2211.09527, 2022.
3. Q. Zhan, Z. Liang, Z. Ying, D. Kang. *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.* arXiv:2403.02691, 2024.
4. E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, F. Tramèr. *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* arXiv:2406.13352, 2024.
5. E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, D. Fabian, C. Kern, C. Shi, A. Terzis, F. Tramèr. *Defeating Prompt Injections by Design.* arXiv:2503.18813, 2025.
6. K. Mei, X. Zhu, W. Xu, W. Hua, M. Jin, Z. Li, S. Xu, R. Ye, Y. Ge, Y. Zhang. *AIOS: LLM Agent Operating System.* arXiv:2403.16971, 2024.
7. J. H. Saltzer, M. D. Schroeder. *The Protection of Information in Computer Systems.* Proceedings of the IEEE, 63(9), 1975. **[verify details before submission]**
8. bubblewrap, unprivileged sandboxing tool. https://github.com/containers/bubblewrap
