# Kafka Events

## Source of truth

This document reflects a scan of the microservices codebase performed on **2026-06-25**.

The review considered:

- `Program.cs` for registered hosted services, producers, consumers, and dispatchers;
- `Infrastructure/Messaging/KafkaOptions.cs` for configured topic names;
- key saga handlers when needed to identify topics written to the outbox.

## Status definitions

| Status | Meaning |
|---|---|
| Implemented | A producer and/or consumer is registered in the current code. |
| Produced without consumer | A service writes the topic, but no consumer was found in the current ecosystem. |
| Configured without producer | A consumer is configured for the topic, but no producer was found. |
| Internal | Saga implementation topic rather than a public canonical business event. |
| Pending | Depends on a microservice or integration that is not implemented yet. |

## Implemented topics

### Shipping promise

| Topic | Producer | Consumer | Practical status |
|---|---|---|---|
| `checkout.shipping.quote.requested` | `CheckoutService` | `ShippingPromiseService`, `AuditService` | Implemented |
| `shipping.promise.calculated` | `ShippingPromiseService` | `CheckoutService`, `AuditService` | Implemented |

### Checkout and order

| Topic | Producer | Consumer | Practical status |
|---|---|---|---|
| `checkout.confirmed` | `CheckoutService` | `OrderService`, `AuditService` | Implemented |
| `order.created` | `OrderService` | `ShipmentService`, `NotificationService`, `AuditService` | Implemented |
| `order.events` | `OrderService` | Internal/controlled consumers | Internal; used for confirmation/cancellation events in the current implementation |

### Inventory saga

| Topic | Producer | Consumer | Practical status |
|---|---|---|---|
| `inventory.commands` | `OrderService` | `InventoryService` | Implemented |
| `inventory.reserved` | `InventoryService` | `OrderService` | Implemented |
| `inventory.reservation.confirmed` | `InventoryService` | `OrderService` | Implemented; `InventoryReservedConsumer` subscribes to both reservation topics |
| `inventory.reservation.failed` | `InventoryService` | `OrderService` | Implemented |
| `inventory.reservation.released` | `InventoryService` | None found | Produced without consumer |
| `inventory.reservation.expired` | `InventoryService` | None found | Produced without consumer |

### Fulfillment saga

| Topic | Producer | Consumer | Practical status |
|---|---|---|---|
| `fulfillment.commands` | `OrderService` | `FulfillmentCenterService` | Implemented |
| `fulfillment.capacity.reserved` | `FulfillmentCenterService` | `OrderService` | Implemented |
| `fulfillment.capacity.confirmed` | `FulfillmentCenterService` | `OrderService` | Implemented; `FulfillmentCapacityReservedConsumer` subscribes to both reserved and confirmed topics |
| `fulfillment.capacity.failed` | `FulfillmentCenterService` | `OrderService` | Implemented |
| `fulfillment.capacity.reservation.expired` | `FulfillmentCenterService` | None found | Produced without consumer |

### Payment

| Topic | Producer | Consumer | Practical status |
|---|---|---|---|
| `payment.commands` | `OrderService` | `PaymentService` | Implemented |
| `payment.approved` | `PaymentService` | `OrderService`, `AuditService` | Implemented |
| `payment.rejected` | `PaymentService` | `NotificationService`, `OrderService`, `AuditService` | Implemented |
| `payment.captured` | `PaymentService` | `OrderService`, `AuditService` | Implemented |
| `payment.capture.failed` | `PaymentService` | `OrderService`, `AuditService` | Implemented |

`PaymentService` does not integrate with a real PSP/payment gateway. It currently uses a deterministic mock adapter. See [Payment Service](../services/payment-service.md).

### Shipment and tracking

| Topic | Producer | Consumer | Practical status |
|---|---|---|---|
| `shipment.commands` | `OrderService` | `ShipmentService` | Implemented |
| `order.created` | `OrderService` | `ShipmentService` | Implemented |
| `shipment.created` | `ShipmentService` | `TrackingService`, `NotificationService`, `OrderService`, `AuditService` | Implemented |
| `shipment.status.updated` | `TrackingService` | `OrderService`, `NotificationService`, `AuditService` | Implemented |
| `carrier-shipment.commands` | `ShipmentService` | None found | Produced without consumer; carrier integration is pending/simulated |

### Cart

| Topic | Producer | Consumer | Practical status |
|---|---|---|---|
| `cart.abandoned` | `MarketplaceWeb.Bff` | `NotificationService` | Implemented |

`MarketplaceWeb.Bff` publishes `cart.abandoned` directly rather than through an outbox. This is deliberate: the cart is ephemeral UX/session state stored in Redis as `cart:<cartOwnerId>`, and losing or duplicating an abandoned-cart reminder has much lower severity than losing a payment or inventory saga event. `NotificationService` handles the event idempotently by `eventId`.

Example payload:

```json
{
  "eventId": "uuid",
  "eventType": "cart.abandoned",
  "schemaVersion": "1.0",
  "occurredAt": "2026-07-04T12:00:00Z",
  "correlationId": "uuid",
  "producer": "marketplaceweb-bff",
  "payload": {
    "cartOwnerId": "buyerId (guid) or anon:<guid>",
    "buyerId": "guid | null",
    "items": [ { "skuId": "guid", "quantity": 1 } ],
    "lastActivityAt": "2026-07-04T11:00:00Z"
  }
}
```

If `buyerId` is `null`, `NotificationService` consumes the event but does not send a reminder because there is no known recipient.

## Topics configured in consumers without an implemented producer

| Topic | Configured consumer | Situation |
|---|---|---|
| `order.confirmed` | `NotificationService` | No canonical producer found. `OrderService` currently writes confirmation to `order.events`. |
| `order.cancelled` | `NotificationService` | No canonical producer found. `OrderService` currently writes cancellation to `order.events`. |
| `shipment.cancelled` | `NotificationService` | No producer exists in the current `ShipmentService`; cancellation writes `carrier-shipment.commands`. |
| `shipment.creation.failed` | `OrderService` | Present in `KafkaOptions`, but no registered `Program.cs` consumer was found. |

## Recommended canonical envelope

```json
{
  "eventId": "uuid",
  "eventType": "shipment.status.updated",
  "schemaVersion": "1.0",
  "occurredAt": "2026-06-14T12:00:00Z",
  "correlationId": "uuid",
  "traceId": "hex-string",
  "spanId": "hex-string",
  "producer": "shipment-service",
  "payload": {}
}
```

Rules:

1. Canonical events represent business facts that have already happened.
2. Internal saga commands must not be presented as canonical events.
3. `eventType` should match the canonical topic name.
4. Command messages (`*.commands`) may use a dedicated contract but still need a `messageId`, aggregate key, and idempotency mechanism.
5. Topics without an implemented producer or consumer must remain explicitly marked as pending/partial.

### Optional `traceId` / `spanId`

These fields were added incrementally so `OrderVisibilityService` can link timeline events directly to Jaeger traces. They are additive and optional. Consumers must not require them; `correlationId` remains the standard fallback.

Adoption status as of 2026-07-02:

| Producer | `traceId`/`spanId` in envelope |
|---|---|
| `CheckoutService` | Implemented for `checkout.shipping.quote.requested` and `checkout.confirmed` |
| `FulfillmentCenterService` | Implemented for capacity reserved/confirmed/failed events |
| `OrderService` | Pending |
| `InventoryService` | Pending |
| `PaymentService` | Pending |
| `ShipmentService` | Pending |
| `TrackingService` | Pending |

Some pending producers create their event envelope only in a background dispatcher, after the original HTTP `Activity` has ended. For those producers, trace information must be captured when writing the outbox record and propagated to the dispatcher. This is follow-up work rather than a blocker because correlation-based Jaeger lookup already works.

## Summary matrix

| Topic | Producer | Main consumer | Classification |
|---|---|---|---|
| `checkout.shipping.quote.requested` | `CheckoutService` | `ShippingPromiseService`, `AuditService` | Implemented event |
| `shipping.promise.calculated` | `ShippingPromiseService` | `CheckoutService`, `AuditService` | Implemented event |
| `checkout.confirmed` | `CheckoutService` | `OrderService`, `AuditService` | Implemented event |
| `order.created` | `OrderService` | `ShipmentService`, `NotificationService`, `AuditService` | Implemented event |
| `inventory.commands` | `OrderService` | `InventoryService` | Implemented internal command |
| `inventory.reserved` | `InventoryService` | `OrderService` | Implemented internal event |
| `inventory.reservation.confirmed` | `InventoryService` | `OrderService` | Implemented internal event |
| `inventory.reservation.failed` | `InventoryService` | `OrderService` | Implemented internal event |
| `inventory.reservation.released` | `InventoryService` | None found | Produced without consumer |
| `inventory.reservation.expired` | `InventoryService` | None found | Produced without consumer |
| `fulfillment.commands` | `OrderService` | `FulfillmentCenterService` | Implemented internal command |
| `fulfillment.capacity.reserved` | `FulfillmentCenterService` | `OrderService` | Implemented internal event |
| `fulfillment.capacity.confirmed` | `FulfillmentCenterService` | `OrderService` | Implemented internal event |
| `fulfillment.capacity.failed` | `FulfillmentCenterService` | `OrderService` | Implemented internal event |
| `fulfillment.capacity.reservation.expired` | `FulfillmentCenterService` | None found | Produced without consumer |
| `payment.commands` | `OrderService` | `PaymentService` | Implemented internal command |
| `payment.approved` | `PaymentService` | `OrderService`, `AuditService` | Implemented event |
| `payment.rejected` | `PaymentService` | `NotificationService`, `OrderService`, `AuditService` | Implemented event |
| `payment.captured` | `PaymentService` | `OrderService`, `AuditService` | Implemented event |
| `payment.capture.failed` | `PaymentService` | `OrderService`, `AuditService` | Implemented event |
| `shipment.commands` | `OrderService` | `ShipmentService` | Implemented internal command |
| `shipment.created` | `ShipmentService` | `TrackingService`, `NotificationService`, `OrderService`, `AuditService` | Implemented event |
| `shipment.status.updated` | `TrackingService` | `OrderService`, `NotificationService`, `AuditService` | Implemented event |
| `carrier-shipment.commands` | `ShipmentService` | None found | Pending |
| `order.events` | `OrderService` | Internal/controlled | Internal |
| `cart.abandoned` | `MarketplaceWeb.Bff` | `NotificationService` | Implemented event without outbox |

## Practical decision

The current end-to-end implementation should be described as **partial**:

- complete for checkout → promise → order → inventory/fulfillment → payment → shipment → tracking/notification;
- audited by `AuditService` for the ten canonical topics that currently have real producers;
- incomplete for some notification events that are configured in consumers but do not yet have a canonical producer.
