OpenTelemetry + Prometheus instrumentation checklist for Blue Planet (10–15 bullets)

Context & assumptions
- Based on the Blue Planet Admin Guide (BPO 24.04) and the `bp charter tools` notes. I don't have live configs; these are implementation-ready recommendations you should validate against the Deployment Guide and actual service endpoints.
- Naming conventions: use `service.name` for OTEL traces and `job`/`instance` labels for Prometheus metrics. Prefix Prometheus metrics with `bp_` or `mdso_` to avoid collisions.

Checklist (instrumentation items)

1. service.name and semantic resource attributes
   - Ensure every process/container sets `service.name` (e.g., `apigw`, `bpocore`, `asset-manager`, `solutionmanager`, `pm`, `bpocore-bpmn`).
   - Populate resource attributes: `deployment.environment`, `hostname`, `container.id`, `k8s.pod.name` (if K8s), `tenant_id`, `domain_id`.

2. HTTP server/client spans (apigw, internal REST calls)
   - Instrument HTTP servers with incoming spans. Attributes: `http.method`, `http.target`, `http.route`, `http.status_code`, `net.peer.ip`, `net.host.port`.
   - Create client spans for inter-service HTTP calls with `http.url` and `http.status_code`.
   - Prometheus metrics: `bp_http_request_total{job,handler,method,status}`, `bp_http_request_duration_seconds_bucket{job,handler}`.

3. Kafka producer/consumer spans and metrics
   - Add messaging spans for producer and consumer with attributes: `messaging.system=kafka`, `messaging.destination` (topic), `messaging.kafka.partition`, `messaging.message_id`.
   - Prometheus metrics: `bp_kafka_producer_messages_total`, `bp_kafka_consumer_lag{group,topic,partition}`, `bp_kafka_bytes_in_total`.

4. Database spans and metrics (Postgres, Galera)
   - Instrument DB queries with `db.system=postgresql|galera`, `db.name`, `db.statement` (or obfuscated), `db.user`.
   - Prometheus metrics: `bp_db_connections`, `bp_db_query_duration_seconds_bucket`, `bp_postgres_replication_lag_seconds`.

5. Template Engine / Service Template lifecycle spans
   - Create spans for lifecycle operations: `template.activate`, `template.update`, `template.terminate`. Attributes: `resource.id`, `resource.type`, `desired_orch_state`, `orch_state`.
   - Prometheus metrics: `bp_template_activations_total`, `bp_template_failures_total`, `bp_template_activation_duration_seconds_bucket`.

6. RA Manager / Resource Adapter interactions
   - Trace RA Manager requests to RAs and events (discovery, resync). Attributes: `ra.id`, `discovery.strategy`, `resync.scope`.
   - Prometheus metrics: `bp_ra_requests_total`, `bp_ra_discovery_errors_total`.

7. Queue and messaging correlation keys
   - When producing events, include correlation IDs (traceparent / trace context) in message envelope headers so consumers can correlate message spans to original traces.
   - Use `trace_id` and `correlation_id` attributes on message spans.

8. Authentication & security events (UAC)
   - Instrument login/login-fail, token generation, API key creation events. Attributes: `user.id`, `tenant.id`, `auth.method`.
   - Prometheus: `bp_auth_success_total`, `bp_auth_fail_total`, `bp_api_keys_created_total`.

9. JVM and process-level metrics
   - Export JVM metrics for Java-based services: heap, non-heap, GC pause, threads. Prometheus names: `bp_jvm_memory_used_bytes`, `bp_jvm_gc_pause_seconds_total`, `bp_process_cpu_seconds_total`, `bp_process_resident_memory_bytes`.

10. Elasticsearch and logging metrics
   - Export ES metrics: index size, doc count, indexing latency. Prometheus: `bp_elasticsearch_index_size_bytes`, `bp_elasticsearch_indexing_latency_seconds`.
   - Ensure logs include structured fields for `service`, `trace_id`, `span_id`, `resource_id`, `orch_state`.

11. Alerts & SLO related metrics
   - Expose `bp_slo_error_ratio` and `bp_slo_latency_seconds_bucket` for key services (apigw, bpocore).
   - Tag metrics with `environment`, `tenant`, and `domain`.

12. Health and liveness probes
   - Export simple `bp_service_up{service}` gauge (1/0) for service discovery and Nagios checks; used by Prometheus alerting rules.

13. Audit trails and obfuscation
   - Add audit spans/events for sensitive ops (credential updates, backup actions). Ensure log obfuscation for credentials is applied via configuration (see Admin Guide obfuscation settings).

14. Sampling & retention
   - Use trace sampling strategy: default 1% global, 100% for error spans (status code >=500) and for resource lifecycle operations. Adjust according to traffic and storage budget.

15. Correlation rules and labels
   - Standardize attribute names: `resource.id`, `domain.id`, `product.id`, `tenant.id`, `orch_state`.
   - Ensure both traces and logs carry these attributes to enable join/correlation in your observability backend.

Quick mapping examples (Prometheus metric <---> service):
- `bp_http_request_total{job="apigw",handler="/api/..."}` <-- apigw
- `bp_kafka_consumer_lag{topic="mdso-events"}` <-- kafka
- `bp_jvm_memory_used_bytes{service="bpocore"}` <-- bpocore
- `bp_postgres_replication_lag_seconds{instance="postgres"}` <-- postgres

If you want, I can expand each item into exact instrumentation snippets (OpenTelemetry SDK examples in Python, Java, and Node) and sample Prometheus metric names/labels; tell me which language(s) to prioritize.