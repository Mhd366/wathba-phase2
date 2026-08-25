# WATHBA user experience architecture

## Coach workspace

- Performance command center across 100m, 200m and 400m.
- Eight-lane squad board and group insights.
- New athlete/video analysis.
- Feature Engineering transparency page.
- Development recommendations with coach approval states.
- Federation PDF report export.

## Athlete portal

- Personal performance overview.
- Simple sprint upload.
- Personal measurements and confidence context.
- Personal development recommendations.
- Personal report history.

## Feature Engineering

The product presents the calculation chain in three layers:

1. Raw: unit-bearing measurements such as SF, SL, GCT, FT, touchdown knee and trunk lean.
2. Dimensionless: duty factor, contact/flight ratio, relative step length, normalised step frequency, Froude number, knee delta and asymmetry.
3. Context: speed, steps, camera angle, FPS and phase govern tier, availability, confidence and precision.

## Recommendation integration

The interface owns presentation, approval state and athlete progress tracking. The AI team owns retrieval and generation. Every returned recommendation must include metric triggers, source identity, confidence, prescription and approval status.

## Chat interaction

The assistant is hidden by default behind a floating button. Opening it must not navigate away from the current athlete or event. Closing it restores the full workspace without losing the conversation state.

