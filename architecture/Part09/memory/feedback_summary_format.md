---
name: feedback_summary_format
description: Learned that user wants summaries in specific analysis/summary block format without tool calls
metadata:
  type: feedback
---

When user asks for conversation summary, provide exactly: <analysis>[concise analysis]</analysis> then <summary>[detailed summary]</summary> with text only, no tool calls, no explanations outside required format. User prohibits tool use when requesting summaries and insists on strict adherence to specified output structure.