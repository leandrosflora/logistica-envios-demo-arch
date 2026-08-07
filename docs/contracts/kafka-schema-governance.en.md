# Kafka Schema Governance — Logistics Marketplace

## Goal

Document the evolution, versioning, and ownership process for canonical Kafka event schemas in the Logistics Marketplace ecosystem.

Related architectural decision: [ADR-0004 — Kafka Schema Versioning Strategy](../adr/0004-kafka-schema-versioning.md).

---

## 1. Change Types and Impact

| Change type | Compatibility | Action |
|---|---|---|
| Add optional field to `payload` | Backward-compatible | Increment minor version: `1.0` → `1.1` |
| Add required field with a default value | Backward-compatible with care | Increment minor version and document the default |
| Remove field | **Breaking** | New major version: `1.x` → `2.0` plus mandatory ADR |
| Rename field | **Breaking** | New major version: `1.x` → `2.0` plus mandatory ADR |
| Change field type | **Breaking** | New major version: `1.x` → `2.0` plus mandatory ADR |
| Change field semantics | **Breaking** | New major version: `1.x` → `2.0` plus mandatory ADR |
| New canonical topic | N/A | PR with specification in `kafka-events.md`; ADR if it introduces a new domain |

---

## 2. Contract Evolution Process

### Backward-compatible change (minor)

1. Create a PR changing the payload in `docs/contracts/kafka-events.md`.
2. Update `schemaVersion` in the event envelope, e.g. `1.0` → `1.1`.
3. Notify consumer owners in the PR using the ownership table below.
4. Obtain approval from at least one reviewer and the topic owner.
5. Merge.

### Breaking change (major)

1. **Before implementation**, create an ADR documenting the change and rationale.
2. The ADR must define a minimum coexistence period — default: 30 days or two production deployments.
3. Create a PR with the new schema version in `kafka-events.md`.
4. Move `schemaVersion` to the new major version, e.g. `1.x` → `2.0`.
5. The producer starts publishing the new payload version.
6. Consumers continue supporting the previous version during coexistence.
7. Once all consumers migrate, deprecate the old version with an explicit removal date.
8. Update the ownership table in this document.

---

## 3. Tolerant Reader Pattern — Required

Every Kafka consumer MUST ignore unknown fields in the payload. This allows additive schema evolution without breaking existing consumers.

### .NET / System.Text.Json

```csharp
// System.Text.Json ignores unknown fields by default
var options = new JsonSerializerOptions
{
    PropertyNameCaseInsensitive = true
};
var payload = JsonSerializer.Deserialize<OrderCreatedPayload>(json, options);
```

### .NET / Newtonsoft.Json

```csharp
var settings = new JsonSerializerSettings
{
    MissingMemberHandling = MissingMemberHandling.Ignore
};
var payload = JsonConvert.DeserializeObject<OrderCreatedPayload>(json, settings);
```

**Rule:** Unknown fields must never cause deserialization failures. If a required business field is absent, the consumer should log the error and move the message to a DLQ rather than fail because of unknown-field handling.

---

## 4. Topic Ownership

| Topic | Schema owner | Producer service | Consumers | Current version | Last change |
|---|---|---|---|---|---|
| `checkout.shipping.quote.requested` | Checkout Service | `checkout-service` | `shipping-promise-service`, `audit-service`, `analytics` | `1.0` | 2026-06-14 |
| `shipping.promise.calculated` | Shipping Promise Service | `shipping-promise-service` | `checkout-service`, `audit-service`, `analytics` | `1.0` | 2026-06-14 |
| `checkout.confirmed` | Checkout Service | `checkout-service` | `order-service`, `audit-service` | `1.0` | 2026-06-21 |
| `order.created` | Order Service | `order-service` | `shipment-service`, `notification-service`, `audit-service` | `1.0` | 2026-06-14 |
| `shipment.created` | Shipment Service | `shipment-service` | `tracking-service`, `notification-service`, `audit-service` | `1.1` | 2026-06-20 — added `sellerId` |
| `shipment.status.updated` | Tracking Service | `tracking-service` | `notification-service`, `audit-service`, `order-service` | `1.0` | 2026-06-14 |
| `order.confirmed` | Order Service | `order-service` | `notification-service`, `audit-service` | `1.0` | 2026-06-20 |
| `order.cancelled` | Order Service | `order-service` | `shipment-service`, `notification-service`, `audit-service`, `inventory-service` | `1.0` | 2026-06-20 |
| `payment.approved` | Payment Service | `payment-service` | `order-service`, `audit-service` | `1.0` | 2026-06-20 |
| `payment.rejected` | Payment Service | `payment-service` | `order-service`, `notification-service`, `audit-service` | `1.0` | 2026-06-20 |
| `shipment.cancelled` | Shipment Service | `shipment-service` | `tracking-service`, `notification-service`, `order-service`, `audit-service` | `1.0` | 2026-06-20 |

---

## 5. Dead Letter Queue (DLQ)

Every canonical topic SHOULD have a corresponding `<topic>.dlq` topic.

| Topic | DLQ |
|---|---|
| `order.created` | `order.created.dlq` |
| `shipment.created` | `shipment.created.dlq` |
| `shipment.status.updated` | `shipment.status.updated.dlq` |
| *(and so on)* | |

Messages sent to a DLQ should carry failure metadata in Kafka headers:

- `dlq-reason`: human-readable failure reason;
- `dlq-original-topic`: original topic;
- `dlq-retry-count`: number of attempts;
- `dlq-correlation-id`: correlation ID of the original message.

---

## 6. References

- [ADR-0004 — Kafka Schema Versioning Strategy](../adr/0004-kafka-schema-versioning.md)
- [ADR-0001 — Event-Driven Architecture](../adr/0001-use-event-driven-architecture.md)
- [Kafka Contracts](kafka-events.md)
