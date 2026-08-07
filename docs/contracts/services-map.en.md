# Microservices Map

## Source of truth

This map reflects a scan of the microservices code repositories performed on **2026-06-25**.

Only services that actually exist as standalone repositories were considered, together with the endpoints, consumers, producers, databases, and caches registered in the code.

## Implemented microservices

| Service | Repo | Type | Main input | Main output | Implementation notes |
|---|---|---|---|---|---|
| Product Search Service | `ProductSearchService` | Read/search | `GET /v1/products/search` | paginated product cards | Uses a Postgres read model through Dapper/Npgsql. OpenSearch is planned evolution, not the current runtime. |
| Checkout Service | `CheckoutService` | Journey | `POST /v1/checkouts`, `POST /v1/checkouts/{id}/confirm` | `checkout.shipping.quote.requested`, `checkout.confirmed` | Supports mock mode when `CheckoutDb` is not configured; consumes `shipping.promise.calculated` when Kafka is configured. |
| Shipping Promise Service | `ShippingPromiseService` | Logistics domain | `POST /v1/shipping-promises`, `checkout.shipping.quote.requested` | `shipping.promise.calculated` | Calls Catalog, Inventory, Fulfillment, Routing, Carrier, and Pricing over HTTP; uses Postgres and Redis. |
| Product Catalog Service | `ProductCatalogService` | Catalog domain | `GET /v1/products/{skuId}/logistics`, `GET /v1/products/logistics/batch` | SKU logistics attributes | Uses Postgres and Redis. Has a local outbox, but no Kafka dispatcher is currently registered at bootstrap. |
| Inventory Service | `InventoryService` | Inventory domain | availability/reservation APIs and `inventory.commands` | `inventory.reserved`, `inventory.reservation.confirmed`, `inventory.reservation.failed`, `inventory.reservation.released` | Uses Postgres, a command consumer, and an outbox dispatcher. |
| Fulfillment Center Service | `FulfillmentCenterService` | Fulfillment domain | FC/capacity APIs and `fulfillment.commands` | `fulfillment.capacity.reserved`, `fulfillment.capacity.confirmed`, `fulfillment.capacity.failed` | Uses Postgres, a command consumer, and an outbox dispatcher. |
| Routing Service | `RoutingService` | Routing domain | `POST /v1/routes/calculate`, `GET /v1/routes/{routeId}` | calculated route and SLA | Uses Postgres/Redis or a mock repository depending on configuration. Kafka is not used in the current bootstrap. |
| Carrier Service | `CarrierService` | Logistics integration | `/v1/carrier-availability/search`, `/v1/carriers/*` | availability, carrier profiles, and rules | Uses Postgres, Redis, and external HTTP adapters. Has a local administrative outbox, but no Kafka dispatcher is currently registered. |
| Shipping Pricing Service | `ShippingPricingService` | Pricing domain | `/v1/pricing/freight`, `/shipping-prices/quotes/*`, `/rate-cards/*` | freight price, quote, and rate cards | Uses Postgres, Redis, and a local pricing engine. Has a local outbox without a registered Kafka dispatcher. |
| Order Service | `OrderService` | Order/saga domain | `checkout.confirmed`, `/orders/*` APIs | `order.created`, `inventory.commands`, `fulfillment.commands`, `payment.commands`, `shipment.commands`, `order.events` | Orchestrates the saga through the outbox. `payment.commands` is consumed by `PaymentService`; `OrderService` consumes `payment.approved`/`payment.rejected`/`payment.captured`/`payment.capture.failed` in return. |
| Payment Service | `PaymentService` | Payment domain | `payment.commands` | `payment.approved`, `payment.rejected`, `payment.captured`, `payment.capture.failed` | Uses Postgres (EF Core), a command consumer, and an outbox dispatcher. No real PSP/gateway integration; it uses a deterministic mock adapter. |
| Shipment Service | `ShipmentService` | Shipment domain | `order.created`, `shipment.commands`, `/shipments/*` APIs | `shipment.created`, `carrier-shipment.commands` | Creates shipment, package, label, and triggers carrier integration. It does not currently publish `shipment.cancelled`. |
| Tracking Service | `TrackingService` | Tracking domain | `shipment.created`, `POST /v1/tracking/events` | `shipment.status.updated` | Maintains the tracking timeline and publishes status updates through the outbox dispatcher. |
| Notification Service | `NotificationService` | Notification platform | Kafka events and `/v1/notifications/*`, `/v1/notification-preferences/*`, `/v1/providers/*/receipts` APIs | Email/SMS/Push delivery and persistence | Consumes configured events; some expected producers still do not exist in the current codebase. |
| Audit Service | `AuditService` | Audit/observability | ten canonical topics with real producers | None (consumer-only) | Uses Postgres through Dapper/Npgsql, not EF Core. Persists the raw canonical envelope immutably and uses an inbox for idempotency. |

## Synchronous quote flow

1. The frontend calls the BFF.
2. The BFF calls `ProductSearchService` for product discovery.
3. Checkout or the BFF calls `ShippingPromiseService` for a quote.
4. `ShippingPromiseService` calls the following services over HTTP:
   - `ProductCatalogService`;
   - `InventoryService`;
   - `FulfillmentCenterService`;
   - `RoutingService`;
   - `CarrierService`;
   - `ShippingPricingService`.
5. The result returns availability, ETA, delivery mode, carrier, and price.

## Implemented asynchronous flow

1. `CheckoutService` publishes `checkout.shipping.quote.requested`.
2. `ShippingPromiseService` consumes it and publishes `shipping.promise.calculated`.
3. `CheckoutService` consumes the calculated promise and can confirm checkout.
4. `CheckoutService` publishes `checkout.confirmed`.
5. `OrderService` consumes `checkout.confirmed`, creates the `Order`, and publishes:
   - `order.created`;
   - `inventory.commands`;
   - `fulfillment.commands`.
6. `InventoryService` and `FulfillmentCenterService` consume commands and publish reservation/confirmation/failure events.
7. Once inventory and capacity are reserved, `OrderService` writes `payment.commands`.
8. `PaymentService` consumes `payment.commands` and publishes `payment.approved`/`payment.rejected` (or `payment.captured`/`payment.capture.failed` during capture); `OrderService` consumes the responses and advances the saga.
9. After payment authorization/capture, `OrderService` writes `shipment.commands` and `order.events`.
10. `ShipmentService` consumes `order.created` and/or `shipment.commands`, creates a shipment, and publishes `shipment.created`.
11. `TrackingService` consumes `shipment.created` and publishes `shipment.status.updated` when tracking events arrive.
12. `NotificationService` consumes configured events and plans/sends notifications.
13. `AuditService` consumes, in parallel, the ten canonical topics that currently have real producers and persists each as an immutable audit entry.

## Data and infrastructure

The database, schema, cache, and Inbox/Outbox matrix is documented in [`data-stores.md`](data-stores.md).

## Scan details

Alignment report: [`../reviews/microservices-code-alignment-2026-06-25.md`](../reviews/microservices-code-alignment-2026-06-25.md).
