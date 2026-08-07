# Domain Glossary — Logistics Marketplace

Formal definitions for the terms used across the Logistics Marketplace ecosystem. AI agents and developers should use this glossary to keep the ubiquitous language consistent across code, contracts, and documentation.

---

## A–C

### Buyer
**Definition:** User who purchases products in the marketplace. Identified by `buyerId` (UUID).
**Usage:** Present in events and contracts related to the purchase journey, including `checkout.shipping.quote.requested`, `order.created`, `shipment.created`, and `shipment.status.updated`.
**Related terms:** Seller, Order, Checkout

### Carrier
**Definition:** Logistics provider responsible for physically moving a package from a fulfillment center to the buyer's destination. Examples include postal operators, private carriers, and last-mile partners.
**Usage:** `Carrier Service`; `carrierCode` field in Kafka and OpenAPI contracts.
**Related terms:** Carrier Service, Route, Service Level, Shipment

### Carrier Service (microservice)
**Definition:** Microservice responsible for carrier integrations, restrictions, available service levels, and delivery options for a specific route and package.
**Usage:** Synchronous dependency of the `Shipping Promise Service`.
**Related terms:** Carrier, Route, Shipping Promise Service

### Checkout
**Definition:** Transactional process that starts when the buyer confirms the purchase of one or more cart items. It includes freight quoting, delivery option selection, payment, and confirmation.
**Usage:** `Checkout Service`, `checkout.shipping.quote.requested`, `checkoutId`.
**Related terms:** Checkout Service, Shipping Promise, Order

### Checkout Service (microservice)
**Definition:** Microservice that orchestrates the user-facing purchase experience, coordinating freight quotes, confirmation, and order creation.
**Usage:** Producer of `checkout.shipping.quote.requested`; consumer of `shipping.promise.calculated`.
**Related terms:** Checkout, BFF, Order Service

### Consumer Group
**Definition:** Kafka consumer-group identifier. Messages from a partition are processed by only one consumer in the group, providing controlled parallelism.
**Usage:** Each microservice has a configured `ConsumerGroupId`, such as `shipment-service`.
**Related terms:** Kafka, Canonical Topic, Internal Topic

### CorrelationId
**Definition:** UUID propagated across every hop of a request, through HTTP headers and Kafka envelopes, to trace an end-to-end journey in logs and distributed traces.
**Usage:** `x-correlation-id` HTTP header; `correlationId` Kafka field; OTEL attribute `correlation.id`.
**Related terms:** x-correlation-id, TraceId, Kafka Envelope

### Corridor
**Definition:** Origin-destination pair in a logistics route, such as São Paulo → Rio de Janeiro, used to calculate delivery time and cost.
**Usage:** `Routing Service`, route and SLA calculation.
**Related terms:** Route, Hub, Logistics Network

### Cutoff
**Definition:** Latest time an order can be accepted and processed while preserving the promised delivery date. Orders received after the cutoff roll to the next business-day promise.
**Usage:** `Fulfillment Center Service`; `estimatedDeliveryDate` calculation in `Shipping Promise Service`.
**Related terms:** Fulfillment Center, SLA, Same Day

---

## D–G

### Delivery Exception
**Definition:** Tracking event that represents a failure or deviation in delivery, such as recipient unavailable, invalid address, or damaged package.
**Usage:** `Tracking Service`; `exceptionCode` in `shipment.status.updated`.
**Related terms:** Tracking Event, Shipment, Notification Service

### Kafka Envelope
**Definition:** Required metadata wrapper around the `payload` of a canonical Kafka event. It includes `eventId`, `eventType`, `schemaVersion`, `occurredAt`, `correlationId`, `producer`, and `payload`.
**Usage:** All canonical topics documented in `docs/contracts/kafka-events.md`.
**Related terms:** Canonical Topic, CorrelationId, SchemaVersion

### EstimatedDeliveryDate
**Definition:** Estimated delivery date calculated from SLA, cutoff, logistics route, and shipping mode.
**Usage:** `estimatedDeliveryDate` and `promisedDeliveryDate` fields in Kafka and OpenAPI contracts.
**Related terms:** Shipping Promise, SLA, Cutoff

### EventId
**Definition:** Globally unique UUID for a specific Kafka event instance. Used by the Inbox Pattern for deduplication.
**Usage:** `eventId` in the Kafka envelope and idempotency key in `inbox_messages`.
**Related terms:** Kafka Envelope, Inbox Pattern, Idempotency

### Fulfillment Center (Distribution Center)
**Definition:** Logistics facility where products are stored, picked, packed, and dispatched for delivery.
**Usage:** `Fulfillment Center Service`; `originNodeId` in `order.created`.
**Related terms:** Fulfillment Center Service, Inventory Service, Cutoff

### Fulfillment Center Service (microservice)
**Definition:** Microservice that manages operational capacity, cutoff times, and fulfillment-center availability.
**Usage:** Synchronous dependency of the `Shipping Promise Service`.
**Related terms:** Fulfillment Center, Cutoff, Shipping Promise Service

---

## H–L

### Hub
**Definition:** Intermediate point in the logistics network where packages are consolidated or redistributed between routes.
**Usage:** `Routing Service`, network and route-SLA calculation.
**Related terms:** Logistics Network, Corridor, Route

### Inbox Pattern
**Definition:** Kafka-consumer idempotency pattern in which the message `eventId` is stored in `inbox_messages` before processing; duplicate messages with the same `eventId` are discarded.
**Usage:** Required for critical Kafka consumers. See [ADR-0005](../adr/0005-idempotency-strategy.md).
**Related terms:** Idempotency, EventId, Outbox Pattern

### Label
**Definition:** Document used to identify and physically track a package with the carrier. It contains a barcode or QR code derived from the `trackingCode`.
**Usage:** `Shipment Service`; `labelObjectKey` in `shipment.created`.
**Related terms:** Shipment Service, Tracking Code, Carrier

### Logistics Network
**Definition:** Network of routes, corridors, hubs, and carriers available to move packages between origins and destinations.
**Usage:** `Routing Service`, route and SLA calculation.
**Related terms:** Route, Hub, Corridor, Carrier

---

## N–O

### Next Day
**Definition:** Delivery service level that promises delivery on the next business day after dispatch.
**Usage:** `mode` or `serviceLevelCode` in promise and shipment contracts.
**Related terms:** Same Day, Standard, Service Level, SLA

### Order
**Definition:** Business entity created after the buyer confirms checkout. It represents a confirmed purchase intent and contains payment, item, and delivery-promise information.
**Usage:** `Order Service`; `order.created`; `orderId`.
**Related terms:** Order Service, Checkout, Shipment

### Order Service (microservice)
**Definition:** Microservice that creates and maintains orders after purchase confirmation and orchestrates the order-creation saga through `OrderProcessManager`.
**Usage:** Producer of order events and consumer of shipment-status updates.
**Related terms:** Saga Orchestrator, OrderProcessManager, Shipment Service

### Outbox Pattern
**Definition:** Reliable Kafka publication pattern in which an event is stored in `outbox_messages` in the same database transaction as the business operation. An asynchronous `OutboxDispatcher` later publishes it to Kafka.
**Usage:** Required for producers of critical domain events. See [ADR-0005](../adr/0005-idempotency-strategy.md).
**Related terms:** Idempotency, Inbox Pattern, EventId

---

## P–R

### Package
**Definition:** Physical shipping unit containing one or more order items. Its weight and dimensions affect freight calculations.
**Usage:** `packages[]` in `order.created`; input to `Shipping Pricing Service`.
**Related terms:** Shipment, Label, Shipping Pricing Service

### Promise Id
**Definition:** Unique identifier for a delivery promise calculated by `Shipping Promise Service` for a specific checkout.
**Usage:** `promiseId` in `shipping.promise.calculated`; `shippingPromiseId` in `order.created`.
**Related terms:** Shipping Promise, Checkout, EstimatedDeliveryDate

### Route
**Definition:** Calculated logistics path between an origin fulfillment center and the buyer's destination, including network, hubs, and carriers.
**Usage:** `Routing Service`; `routeId` in `order.created`.
**Related terms:** Routing Service, Logistics Network, Corridor

### Routing Service (microservice)
**Definition:** Microservice that calculates routes, network paths, hubs, and delivery windows for an origin and destination.
**Usage:** Synchronous dependency of `Shipping Promise Service`.
**Related terms:** Route, Logistics Network, Hub

---

## S

### Same Day
**Definition:** Delivery service level that promises delivery on the purchase date, subject to the fulfillment center cutoff.
**Usage:** `mode` or `serviceLevelCode` with value `same_day`.
**Related terms:** Next Day, Standard, Cutoff, Service Level

### SchemaVersion
**Definition:** Version of a Kafka event payload schema in `<major>.<minor>` format, such as `1.0` or `1.1`. Governed by [ADR-0004](../adr/0004-kafka-schema-versioning.md).
**Usage:** `schemaVersion` in all canonical Kafka envelopes.
**Related terms:** Kafka Envelope, Schema Versioning

### Seller
**Definition:** Merchant offering products in the marketplace. Identified by `sellerId` (UUID).
**Usage:** Checkout, quote, and order contracts; delivery-status notifications.
**Related terms:** Buyer, Order, Shipment

### Service Level
**Definition:** Contracted delivery level such as `same_day`, `next_day`, or `standard`. It determines promised delivery time and freight cost.
**Usage:** `serviceLevelCode` and `mode` in Kafka and OpenAPI contracts.
**Related terms:** SLA, Carrier, Route

### Shipment
**Definition:** Entity representing physical delivery of an order: label, package, tracking code, and delivery state. Created by `Shipment Service` after receiving `order.created`.
**Usage:** `Shipment Service`; `shipment.created`; `shipmentId`.
**Related terms:** Shipment Service, Label, Tracking Code

### Shipment Service (microservice)
**Definition:** Microservice responsible for creating the physical shipment, generating the label, defining package information, and managing the shipment lifecycle.
**Usage:** Consumer of `order.created`; producer of `shipment.created`.
**Related terms:** Shipment, Label, Tracking Service

### Shipping Promise
**Definition:** Result of calculating delivery time, availability, shipping mode, carrier, and freight cost for a set of items and a destination.
**Usage:** `Shipping Promise Service`; `shipping.promise.calculated`.
**Related terms:** Shipping Promise Service, EstimatedDeliveryDate, Service Level

### Shipping Promise Service (microservice)
**Definition:** Central service in the quote flow. It receives item and destination data, calls synchronous dependencies, and returns the delivery promise.
**Usage:** Consumer of `checkout.shipping.quote.requested`; producer of `shipping.promise.calculated`. Dependencies include Product Catalog, Inventory, Fulfillment Center, Routing, Carrier, and Pricing.
**Related terms:** Shipping Promise, Checkout Service, Product Catalog Service

### SKU (Stock Keeping Unit)
**Definition:** Unique identifier for a product variation, such as a specific product/color/size combination.
**Usage:** `skuId` in quoting, inventory, and product-catalog contracts.
**Related terms:** Product Catalog Service, Inventory Service, Package

### SLA (Service Level Agreement)
**Definition:** Service agreement defining the maximum delivery time for a route and delivery mode. Example: Same Day delivery by 23:59 for purchases made before 14:00.
**Usage:** Calculated by `Routing Service` and `Shipping Promise Service`.
**Related terms:** SLO, Service Level, EstimatedDeliveryDate

### SLO (Service Level Objective)
**Definition:** Internal reliability/performance objective for a microservice, such as 99.9% availability or P99 latency below 200 ms.
**Usage:** Documented in `docs/services/<name>-service.md` for each microservice.
**Related terms:** SLA, Observability

### Standard
**Definition:** Standard delivery mode with a typical 3–7 business-day promise and lower freight cost.
**Usage:** `mode` or `serviceLevelCode` with value `standard`.
**Related terms:** Same Day, Next Day, Service Level

### Freight Subsidy
**Definition:** Discount funded by the marketplace or seller to reduce the freight amount charged to the buyer.
**Usage:** `Shipping Pricing Service`, final freight-price calculation.
**Related terms:** Shipping Pricing Service, Cost, Service Level

---

## T

### Canonical Topic
**Definition:** Kafka topic representing a public business event with a stable contract, `schemaVersion`, and explicit owner. Documented in `docs/contracts/kafka-events.md`.
**Usage:** Topics such as `order.created`, `shipment.created`, and `shipment.status.updated`.
**Related terms:** Internal Topic, Kafka Envelope, SchemaVersion

### Internal Topic (Saga)
**Definition:** Kafka topic used internally by `OrderService` to orchestrate the order-creation saga. Other domains should not consume it without an architectural decision. See [ADR-0007](../adr/0007-order-service-internal-saga-topics.md).
**Usage:** `inventory.commands`, `fulfillment.commands`, `payment.commands`, `shipment.commands`, `order.events`.
**Related terms:** Canonical Topic, Saga Orchestrator, Order Service

### Tracking Code
**Definition:** Unique alphanumeric identifier used by the carrier to physically track a shipment, for example `BR123456789`.
**Usage:** `trackingCode` in `shipment.created` and `shipment.status.updated`.
**Related terms:** Tracking Service, Shipment, Carrier

### Tracking Event
**Definition:** Shipment status update generated by a carrier or by `Tracking Service`, such as `in_transit`, `out_for_delivery`, `delivered`, or `delivery_failed`.
**Usage:** `Tracking Service`; `currentStatus` in `shipment.status.updated`.
**Related terms:** Tracking Service, Shipment, Delivery Exception

### Tracking Service (microservice)
**Definition:** Microservice responsible for receiving delivery-status updates, maintaining the timeline, and publishing `shipment.status.updated`.
**Usage:** Consumer of `shipment.created`; producer of `shipment.status.updated`.
**Related terms:** Tracking Code, Tracking Event, Notification Service
