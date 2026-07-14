# Validation Plan

## Unit
normalization, dedupe, participant reference, mixed script, protected span, storage uniqueness, deterministic ordering.

## Integration
save, recall, gate, prompt candidate, shadow logging.

## Conversation scenarios
名前, 誕生日, 好み, 第三者, 訂正, 否定, Mixed Script, future plan, long gap, unknown information.

## Long-run
100T, 300T, 500T.

## Human evaluation
Accuracy, naturalness, lover-like tone, persistence/しつこさ, hallucination, irrelevant memory intrusion, prompt growth.

## Promotion criteria
Move from Shadow to Prompt A/B only when useful examples exist, major false recall is tolerable, prompt size is bounded, rollback is ready, and feature flag default is OFF.
