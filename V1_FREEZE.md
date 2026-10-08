# AgentOS v1 Feature Freeze

Freeze marker: `v1-freeze`

Day 5 establishes the first integration freeze. The feature set covering the runtime, four schedulers, monitor, policy enforcement, untrusted-content tagging, tool boundary, local/mock LLM interface, shell client, and v1 runtime memory is frozen.

After this point, only bug fixes, test fixes, documentation corrections, and reproducibility fixes should be merged into the v1 baseline. New features belong in post-freeze branches.

Recommended Git operation after the final merge to `main`:

```powershell
git checkout main
git pull
git tag -a v1-freeze -m "AgentOS v1 feature freeze"
git push origin v1-freeze
```
