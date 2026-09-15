# AgentFabric

**AgentFabric is a resume-focused control plane and runtime for operating autonomous AI agent workflows.**

It allows users to create and run multi-agent workflows, observe what agents are doing in real time, inspect their tool calls and execution history, intervene when necessary, approve potentially sensitive actions, and analyze basic performance and cost metrics.

---

## Mental model

The simplest mental model for AgentFabric is:

```text
                    USER
                      |
                      v
                AGENTFABRIC UI
                      |
                      v
              AGENT ORCHESTRATOR
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      RESEARCHER    CODER      REVIEWER
          |           |           |
          +-----------+-----------+
                      |
                      v
                 TOOL LAYER
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
        APIs        MCP        Other Tools
                      |
                      v
              EXECUTION EVENTS
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
       STORAGE     TRACING     METRICS
                      |
                      v
              AGENTFABRIC CONTROL PLANE
```

The key idea is that AgentFabric is responsible for the **execution and operational visibility around agents**, not for being the model itself.

---

## Current Status

Right now there is 1 agent that is simply finding and reading a file.
