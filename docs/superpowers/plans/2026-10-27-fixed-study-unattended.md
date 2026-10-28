# User-authorized unattended completion

User explicitly overrides the earlier per-failure stop rule: retain individual runtime/scoring errors and continue remaining never-started cells. Disable scheduled monitoring; user will ask tomorrow. No retries of started cells, no score filling, no changes to frozen generation/model/parser/timeouts/scorer.

Implement an immutable `continue_on_error` authorization only in a new named operations session. Unknown owners, evidence corruption and service/process failures retain management stops. Native audit reports all failures honestly; separate coverage accepts only complete880 terminal cells with no native issues other than the recorded runtime/scoring errors.

Tests first: real concurrent remaining-only claims through new runtime/scoring failures; byte preservation; evidence/unknown-start blocking; honest final coverage. Then Linux tests/review, signal only the verified current controller to drain in-flight tasks, seal all drained evidence, start two unchanged owned replicas and verify new claims. No new heartbeat. Background transition may wait for draining without inference interruption.
