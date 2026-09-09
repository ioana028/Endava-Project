# Partner and Commerce Rules

## Partner value proposition

Suzanne demonstrates an in-cabin two-sided marketplace for charging, food,
vignettes, and other journey services. It is still a smart route planner when
no partner is available. Recommendations should be useful to the driver first
and commercially relevant second.

Partner benefits may include discounts or priority, but Suzanne must explain
the driver benefit and preserve an explicit choice through voice. The current
prototype must not add on-screen confirmation buttons.

Partner enrichment is optional. Generic POI search must be able to return a
food, coffee, rest, or destination restaurant result without a partner offer.

## Consent

The driver must explicitly approve a booking or purchase by voice. The
assistant may speak a confirmation request, but it must not represent a
transaction as complete before the commerce service returns a successful
simulated result. No on-screen confirmation button is part of the interaction.

## Prototype limits

- No real card processing.
- No raw card credentials.
- No real hotel booking required.
- No real money movement.
- Wallet data is tokenized/demo-only display data.
- Provider calls may be faked with fixture-backed adapters.

## Future voice confirmation shape

```text
Suzanne: "The Hungarian motorway e-vignette is EUR 16.40. Should I purchase
it with your in-car wallet?"

Driver: "Yes."

Suzanne: "Purchase confirmed. Receipt sent to your email."
```
