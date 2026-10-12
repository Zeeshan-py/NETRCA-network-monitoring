-- DEVELOPMENT ONLY. Static fixtures, never live Mininet/ML/Gemini output.
-- Apply with seed_local.py; migrations never include this file.
-- Stable IDs make repeated application a no-op; existing rows are not overwritten.

INSERT INTO public.devices (id, name, device_type, ip_address, status, metadata)
VALUES ('05d50c12-c3a0-55c0-877a-1f1491f84f94', 'DEMO-R1', 'ROUTER', '10.77.0.1', 'DOWN', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.devices (id, name, device_type, ip_address, status, metadata)
VALUES ('e91444e2-2c6f-59f4-9fc9-d41b662e7214', 'DEMO-S1', 'SWITCH', NULL, 'WARNING', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.devices (id, name, device_type, ip_address, status, metadata)
VALUES ('247fd2e3-fd24-5f3e-b798-babffc370f70', 'DEMO-Server1', 'SERVER', '10.77.0.10', 'WARNING', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.links (id, source_device_id, destination_device_id, bandwidth_mbps, latency_ms, packet_loss_percent, status, metadata)
VALUES ('195b92f7-e9a1-533e-b923-ffb8a2e60888', '05d50c12-c3a0-55c0-877a-1f1491f84f94', 'e91444e2-2c6f-59f4-9fc9-d41b662e7214', 100, 10, 0, 'DOWN', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.links (id, source_device_id, destination_device_id, bandwidth_mbps, latency_ms, packet_loss_percent, status, metadata)
VALUES ('6fab58fa-4987-5c0f-8597-2dda64a3075f', 'e91444e2-2c6f-59f4-9fc9-d41b662e7214', '247fd2e3-fd24-5f3e-b798-babffc370f70', 100, 10, 0, 'UP', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.services (id, name, service_type, port, protocol, status, metadata)
VALUES ('e17fd4b8-aa4e-5413-895f-d5cfd2aeccb0', 'DEMO web service', 'HTTP', 8080, 'TCP', 'DOWN', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.device_services (id, device_id, service_id, status)
VALUES ('1e51f351-96e7-5896-9324-e7d400650831', '247fd2e3-fd24-5f3e-b798-babffc370f70', 'e17fd4b8-aa4e-5413-895f-d5cfd2aeccb0', 'DOWN')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.metrics (id, device_id, link_id, metric_type, value, unit, expected_value, timestamp, metadata)
VALUES ('9b0cdbbc-ec26-542a-bb43-1a9ca7889663', '05d50c12-c3a0-55c0-877a-1f1491f84f94', '195b92f7-e9a1-533e-b923-ffb8a2e60888', 'LATENCY', 10, 'ms', 10, '2026-10-01T09:59:00Z', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.metrics (id, device_id, link_id, metric_type, value, unit, expected_value, timestamp, metadata)
VALUES ('eddfd1ad-5b9c-5fae-a7c6-7dd2f3ffacc9', '05d50c12-c3a0-55c0-877a-1f1491f84f94', '195b92f7-e9a1-533e-b923-ffb8a2e60888', 'PACKET_LOSS', 100, '%', 0, '2026-10-01T10:00:01Z', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.logs (id, device_id, severity, event_type, message, source, timestamp, metadata)
VALUES ('a9bada2c-881e-5654-85a4-d82386d49384', '05d50c12-c3a0-55c0-877a-1f1491f84f94', 'ERROR', 'INTERFACE_FAILURE', 'DEMO: uplink interface disabled.', 'development-seed', '2026-10-01T10:00:00Z', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.events (id, device_id, service_id, event_type, severity, message, status, timestamp, metadata)
VALUES ('ef2317ce-2a9b-53bd-bb7f-dc7e1d8aa99e', '05d50c12-c3a0-55c0-877a-1f1491f84f94', NULL, 'INTERFACE_FAILURE', 'HIGH', 'DEMO: INTERFACE_FAILURE', 'DETECTED', '2026-10-01T10:00:00Z', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.events (id, device_id, service_id, event_type, severity, message, status, timestamp, metadata)
VALUES ('406bc67f-5e93-5d3b-a5a0-4e7398b889b6', '247fd2e3-fd24-5f3e-b798-babffc370f70', 'e17fd4b8-aa4e-5413-895f-d5cfd2aeccb0', 'SERVER_TIMEOUT', 'HIGH', 'DEMO: SERVER_TIMEOUT', 'DETECTED', '2026-10-01T10:00:03Z', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.anomalies (id, device_id, metric_id, event_id, model_name, anomaly_score, is_anomaly, severity, detected_at, features, metadata)
VALUES ('f0b65b4f-a95d-5ec2-b42f-514c1a4bb1e5', '05d50c12-c3a0-55c0-877a-1f1491f84f94', 'eddfd1ad-5b9c-5fae-a7c6-7dd2f3ffacc9', 'ef2317ce-2a9b-53bd-bb7f-dc7e1d8aa99e', 'DEMO-FIXTURE-NO-MODEL-RUN', 0.99, true, 'HIGH', '2026-10-01T10:00:02Z', '{"packet_loss": 100}', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.incidents (id, title, description, severity, status, start_time, root_cause_summary, confidence, impact_summary)
VALUES ('738c7634-2a2b-58b9-beed-a62853c7b7d3', 'DEMO: router uplink failure', 'Static development fixture; no Mininet or analysis engine was run.', 'HIGH', 'ROOT_CAUSE_IDENTIFIED', '2026-10-01T10:00:00Z', 'DEMO: disabled R1 uplink', 0.95, 'DEMO: web service unreachable through R1')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.incident_events (id, incident_id, event_id, sequence_number, relationship_type)
VALUES ('b339fb53-50ac-515a-9b8a-61ddf6b08b15', '738c7634-2a2b-58b9-beed-a62853c7b7d3', 'ef2317ce-2a9b-53bd-bb7f-dc7e1d8aa99e', 1, 'INITIAL_FAILURE')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.incident_events (id, incident_id, event_id, sequence_number, relationship_type)
VALUES ('71f9f99a-eab6-57d6-b17f-15301596d13d', '738c7634-2a2b-58b9-beed-a62853c7b7d3', '406bc67f-5e93-5d3b-a5a0-4e7398b889b6', 2, 'DOWNSTREAM_SYMPTOM')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.root_causes (id, incident_id, cause_type, device_id, link_id, description, confidence, analysis_method, identified_at, metadata)
VALUES ('d4432d50-0914-55ab-b7ab-4c8c5f379b60', '738c7634-2a2b-58b9-beed-a62853c7b7d3', 'INTERFACE_FAILURE', '05d50c12-c3a0-55c0-877a-1f1491f84f94', '195b92f7-e9a1-533e-b923-ffb8a2e60888', 'DEMO: disabled uplink preceded downstream timeout.', 0.95, 'DEVELOPMENT_FIXTURE', '2026-10-01T10:00:04Z', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.topology_snapshots (id, snapshot_time, topology_data, reason)
VALUES ('0bbc61ba-5984-537b-8b46-0d78c31b304e', '2026-10-01T09:59:00Z', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true, "nodes": ["05d50c12-c3a0-55c0-877a-1f1491f84f94", "e91444e2-2c6f-59f4-9fc9-d41b662e7214", "247fd2e3-fd24-5f3e-b798-babffc370f70"], "links": [{"id": "195b92f7-e9a1-533e-b923-ffb8a2e60888", "source": "05d50c12-c3a0-55c0-877a-1f1491f84f94", "target": "e91444e2-2c6f-59f4-9fc9-d41b662e7214"}, {"id": "6fab58fa-4987-5c0f-8597-2dda64a3075f", "source": "e91444e2-2c6f-59f4-9fc9-d41b662e7214", "target": "247fd2e3-fd24-5f3e-b798-babffc370f70"}]}', 'DEMO: pre-failure topology')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.root_cause_evidence (id, root_cause_id, source_type, source_id, description, importance, timestamp)
VALUES ('67e261e1-f4a5-5dc5-8ea2-780e98ebe1e2', 'd4432d50-0914-55ab-b7ab-4c8c5f379b60', 'METRIC', 'eddfd1ad-5b9c-5fae-a7c6-7dd2f3ffacc9', 'DEMO: metric supports this fixture.', 'HIGH', '2026-10-01T10:00:00Z')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.root_cause_evidence (id, root_cause_id, source_type, source_id, description, importance, timestamp)
VALUES ('37c0790d-9d0c-5883-afce-1322a163f4df', 'd4432d50-0914-55ab-b7ab-4c8c5f379b60', 'LOG', 'a9bada2c-881e-5654-85a4-d82386d49384', 'DEMO: log supports this fixture.', 'HIGH', '2026-10-01T10:00:00Z')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.root_cause_evidence (id, root_cause_id, source_type, source_id, description, importance, timestamp)
VALUES ('8dc19155-4c5f-5e73-9d45-d9b8df0fd10f', 'd4432d50-0914-55ab-b7ab-4c8c5f379b60', 'EVENT', 'ef2317ce-2a9b-53bd-bb7f-dc7e1d8aa99e', 'DEMO: event supports this fixture.', 'HIGH', '2026-10-01T10:00:00Z')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.root_cause_evidence (id, root_cause_id, source_type, source_id, description, importance, timestamp)
VALUES ('ec68a904-2ac6-5214-9c77-fca6fdd40c03', 'd4432d50-0914-55ab-b7ab-4c8c5f379b60', 'ANOMALY', 'f0b65b4f-a95d-5ec2-b42f-514c1a4bb1e5', 'DEMO: anomaly supports this fixture.', 'HIGH', '2026-10-01T10:00:00Z')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.root_cause_evidence (id, root_cause_id, source_type, source_id, description, importance, timestamp)
VALUES ('e48a4999-8e26-5c03-bff3-3e19fc27fa40', 'd4432d50-0914-55ab-b7ab-4c8c5f379b60', 'TOPOLOGY', '0bbc61ba-5984-537b-8b46-0d78c31b304e', 'DEMO: topology supports this fixture.', 'HIGH', '2026-10-01T10:00:00Z')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.impact_records (id, incident_id, device_id, service_id, impact_type, severity, description, detected_at, metadata)
VALUES ('aeef6466-9622-553a-b61f-f66dc4d52c23', '738c7634-2a2b-58b9-beed-a62853c7b7d3', '247fd2e3-fd24-5f3e-b798-babffc370f70', 'e17fd4b8-aa4e-5413-895f-d5cfd2aeccb0', 'SERVICE_AFFECTED', 'HIGH', 'DEMO: HTTP unreachable through R1.', '2026-10-01T10:00:03Z', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.recommendations (id, incident_id, root_cause_id, title, description, priority, source, confidence, status)
VALUES ('d7add13c-909d-549d-8e9b-63d9c8303902', '738c7634-2a2b-58b9-beed-a62853c7b7d3', 'd4432d50-0914-55ab-b7ab-4c8c5f379b60', 'DEMO: inspect simulated uplink', 'Check interface state, restore simulated interface, verify HTTP reachability.', 'HIGH', 'RULE', 0.95, 'PENDING')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.ai_analyses (id, incident_id, analysis_type, model_name, input_context, output_text, structured_output)
VALUES ('54423037-49f1-5f1a-b3b9-297903c5a985', '738c7634-2a2b-58b9-beed-a62853c7b7d3', 'INCIDENT_EXPLANATION', 'DEMO-FIXTURE-NOT-GEMINI', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}', 'DEMO static explanation: uplink loss precedes timeout. No AI request was made.', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.fault_injections (id, fault_type, device_id, link_id, severity, parameters, started_at, status)
VALUES ('33724e20-9285-5347-89b7-1f38a1b280bc', 'INTERFACE_FAILURE', '05d50c12-c3a0-55c0-877a-1f1491f84f94', '195b92f7-e9a1-533e-b923-ffb8a2e60888', 'HIGH', '{"demo": true, "source": "phase2-development-seed", "not_live_telemetry": true, "interface": "r1-eth0"}', '2026-10-01T10:00:00Z', 'ACTIVE')
ON CONFLICT (id) DO NOTHING;
