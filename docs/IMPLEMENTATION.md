# Implementation

## Architecture

AgentOS is implemented as an application/system layer on top of Linux. The runtime separates task management, scheduling, agent dispatch, policy enforcement, tool execution, model inference, and monitoring.

```text
User / AI Shell
      |
      v
FastAPI API (/api/task)
      |
      v
Task Manager ---> Scheduler <--- System Monitor
      |                 |
      |                 v
      |            execution decision
      v
Agent Manager
      |
      v
Agent (General / File / Security)
      |
      | every OS-facing capability request
      v
Policy Layer (enforcement on/off)
      |
      v
Tool Registry -> filesystem / system_info
      |
      v
Tool result tagged as UNTRUSTED
      |
      v
LLM / TaskResult
```

The policy layer is the mandatory capability boundary. Agents do not directly invoke filesystem or system-information implementations. They request a named tool through `run_tool(agent, tool, args)`, and the policy engine decides whether the request is allowed before resolving the registered implementation.

## Request Flow

1. The shell or API submits a task.
2. The Task Manager records the task and places it in the scheduler queue.
3. The Scheduler selects the next task using the configured strategy and current system state.
4. The Agent Manager selects the appropriate agent.
5. The runtime configures the selected model tier and assigns the task identifier to the agent execution context.
6. If the agent needs an OS-facing capability, it calls the central `run_tool` boundary.
7. The Policy Layer evaluates the agent/tool combination. With enforcement enabled, disallowed calls are blocked and a `tool_blocked` metric event is recorded. With enforcement disabled, the same boundary remains in place but authorization is bypassed for the Day 6 ablation.
8. Allowed tool calls execute through the Tool Registry.
9. File contents, logs, and tool output are wrapped with explicit `UNTRUSTED_CONTENT` markers before being supplied to the LLM.
10. The agent returns its response to the runtime, which records the final `TaskResult` and experiment metrics.

## Day 4 Policy Ablation Contract

`AGENTOS_POLICY_ENFORCEMENT=on` is the normal secure configuration. `AGENTOS_POLICY_ENFORCEMENT=off` disables authorization decisions for experimental comparison while retaining the same tool boundary and execution path. This makes the Day 6 comparison an implementation-level ablation rather than a separate code path.
