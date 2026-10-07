# Local demo

Start with `python run_local.py` from the configured environment and open
http://127.0.0.1:8501. Select A and auto mode for the recommended workflow.

| Request | What to demonstrate |
|---|---|
| REQ-1001 | $800 add-on; Manager approval; check existing signing agreement |
| REQ-1002 | Approved design alternatives; stated usability gap; new-vendor Security/Legal reviews |
| REQ-1003 | Approved coding vendor still needs scope-specific Security review |
| REQ-1005 | Sales has $18,000 available for a $22,000 request; $4,000 shortfall; PII/overseas reviews |
| REQ-1006 | Unknown amount/seats/access; embedded CFO approval is ignored |
| REQ-1007 | Registry says approved while service says expired; surface both records |
| REQ-1009 | Intentional API 503; no favorable vendor status inferred |
| REQ-1010 | Low-risk training; Manager approval; inspect existing agreement without inventing spare seats |

For each case, inspect the evidence references and next step, then open Human
handoff and download the package. There is no approval or purchase button.

Switch to B to inspect analyst and reviewer traces. Switching request or
architecture clears the previous decision. Offline mode demonstrates rules
without a key; its warning must remain visible. Live mode is useful for strict
evaluation because model failure cannot silently become an offline success.

Try a custom request with a blank amount or unknown data access. It should ask
for clarification. Do not enter real customer data, confidential documents or
credentials into this synthetic demo.
