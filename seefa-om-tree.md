# seefa-om Repository Tree

```
seefa-om/
├── .gitattributes
├── .gitignore
├── .gitlab-ci.yml
├── Makefile
├── docker-compose.selenium.yml
├── docker-compose.yml
├── correlation-engine/
│   ├── .dockerignore
│   ├── .env.example
│   ├── CHANGELOG.md
│   ├── Dockerfile
│   ├── INTEGRATION_SUMMARY.md
│   ├── MIGRATION.md
│   ├── Makefile
│   ├── README.md
│   ├── REDIS-TELEMETRY-FLOW.md
│   ├── docker-compose.yml
│   ├── pip.conf
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── config_demo.py
│   │   ├── database.py
│   │   ├── database_schema.sql
│   │   ├── dependencies.py
│   │   ├── globals.py
│   │   ├── main.py
│   │   ├── mdso_patterns.py
│   │   ├── models.py
│   │   ├── observability.py
│   │   ├── pdf_generator.py
│   │   ├── profiling.py
│   │   ├── redis_schema.py
│   │   ├── seca_scraper.py
│   │   ├── seca_xlsx_processor.py
│   │   ├── selenium_scraper.py
│   │   ├── correlation/
│   │   │   ├── __init__.py
│   │   │   ├── link_resolver.py
│   │   │   ├── span_injector.py
│   │   │   └── trace_synthesizer.py
│   │   ├── mdso/
│   │   │   ├── REPOSITORY_PATTERN.md
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── error_analyzer.py
│   │   │   ├── log_collector.py
│   │   │   ├── models.py
│   │   │   └── repository.py
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── correlator.py
│   │   │   ├── exporters.py
│   │   │   ├── mdso_correlator.py
│   │   │   ├── normalizer.py
│   │   │   └── state_manager.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── correlations.py
│   │   │   ├── docs.py
│   │   │   ├── file_upload.py
│   │   │   ├── health.py
│   │   │   ├── learning.py
│   │   │   ├── logs.py
│   │   │   ├── mdso.py
│   │   │   ├── otlp.py
│   │   │   ├── seca.py
│   │   │   ├── seca_data.py
│   │   │   ├── seca_jobs.py
│   │   │   ├── seca_reviews.py
│   │   │   └── user_auth.py
│   │   ├── tasks/
│   │   │   └── seca_tasks.py
│   │   └── utils/
│   │       └── pdf_report.py
│   ├── docker/
│   │   └── worker.Dockerfile
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_api.py
│       ├── test_config.py
│       ├── test_correlation_index.py
│       ├── test_dependencies.py
│       ├── test_exporters.py
│       ├── test_exporters_edge_cases.py
│       ├── test_health.py
│       ├── test_integration.py
│       ├── test_mdso_client.py
│       ├── test_mdso_extraction.py
│       ├── test_mdso_repository.py
│       ├── test_models.py
│       ├── test_normalizer.py
│       ├── test_pdf_report.py
│       ├── test_pipeline.py
│       ├── test_queue_backpressure.py
│       ├── test_request_size_limits.py
│       ├── test_seca_processor.py
│       ├── test_seca_reformat.py
│       ├── test_seca_traceback.py
│       ├── test_state_manager.py
│       └── test_trace_validation.py
├── docs/
│   ├── CORRELATION_ENHANCEMENTS_IMPLEMENTATION.md
│   ├── CORRELATION_STATION_UI.md
│   ├── DATA_FLOW_DIAGRAM.md
│   ├── DATA_PIPELINE_ANALYSIS.md
│   ├── DEMO_BRANCH_GUIDE.md
│   ├── EXPLORATION_SUMMARY.txt
│   ├── FIXES_SUMMARY.md
│   ├── FRONTEND_FEATURES_COMPLETE.md
│   ├── HORIZONTAL_SCALING.md
│   ├── HORIZONTAL_SCALING_SETUP_GUIDE.md
│   ├── IMPLEMENTATION_GUIDE.md
│   ├── MAKEFILE_SETUP_GUIDE.md
│   ├── MASTER_SETUP_GUIDE.md
│   ├── MDSO_OTEL_INSTRUMENTATION_FINDINGS.md
│   ├── METRICS_CARDINALITY_GUIDE.md
│   ├── OBSERVABILITY_PLATFORM_COMPREHENSIVE_GUIDE.md
│   ├── QUICK_FIX.md
│   ├── README.md
│   ├── RISKS.md
│   ├── ROLLOUT.md
│   ├── RUNBOOK.md
│   ├── SENSE_OTEL_IMPLEMENTATION_SUMMARY.md
│   ├── TESTING_GUIDE.md
│   ├── TEST_IMPROVEMENTS.md
│   ├── api.md
│   ├── architecture.md
│   ├── deployment.md
│   ├── gittlab-setup.md
│   ├── nginx-docker-compose.md
│   ├── prompt.txt
│   ├── setupGuide.md
│   ├── troubleshooting.md
│   ├── adr/
│   │   ├── README.md
│   │   ├── 001-ssl-certificate-verification.md
│   │   ├── 004-repository-pattern-mdso.md
│   │   ├── 005-redis-state-externalization.md
│   │   └── 007-shared-library-extraction.md
│   └── implementation/
│       ├── DEPLOYMENT_GUIDE.md
│       ├── README.md
│       └── USAGE_EXAMPLES.md
├── frontend/
│   ├── .dockerignore
│   ├── .eslintrc.cjs
│   ├── .gitignore
│   ├── Dockerfile
│   ├── desktop.ini
│   ├── index.html
│   ├── nginx.conf
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── index.css
│       ├── main.tsx
│       ├── components/
│       │   ├── CodeBlock.tsx
│       │   ├── DocsLayout.tsx
│       │   ├── DocsSidebar.tsx
│       │   ├── ErrorBanner.tsx
│       │   ├── HealthRow.tsx
│       │   ├── KpiCard.tsx
│       │   ├── Layout.tsx
│       │   ├── LoginModal.tsx
│       │   ├── QuickLinkCard.tsx
│       │   ├── SecaUploadModal.tsx
│       │   ├── TableOfContents.tsx
│       │   ├── app-sidebar.tsx
│       │   ├── site-header.tsx
│       │   └── ui/
│       │       ├── avatar.tsx
│       │       ├── badge.tsx
│       │       ├── button.tsx
│       │       ├── card.tsx
│       │       ├── dialog.tsx
│       │       ├── dropdown-menu.tsx
│       │       ├── input.tsx
│       │       ├── progress.tsx
│       │       ├── select.tsx
│       │       ├── separator.tsx
│       │       ├── sidebar.tsx
│       │       ├── tabs.tsx
│       │       └── tooltip.tsx
│       ├── lib/
│       │   ├── auth.ts
│       │   ├── httpClient.ts
│       │   ├── progress.ts
│       │   └── utils.ts
│       └── pages/
│           ├── ArchitecturePage.tsx
│           ├── CompliancePage.tsx
│           ├── CorrelationEnginePage.tsx
│           ├── DocumentationPage.tsx
│           ├── ForgotPasswordPage.tsx
│           ├── HomePage.tsx
│           ├── LoginPage.tsx
│           ├── NetDev101Page.tsx
│           ├── ResetPasswordPage.tsx
│           ├── SecaReviewsPage.tsx
│           ├── SecaUploadPage.tsx
│           └── TutorialsPageNew.tsx
├── gateway/
│   ├── .env.example
│   ├── Dockerfile
│   ├── README.md
│   ├── docker-compose.txt
│   └── otel-config.yaml
├── k6/
│   ├── README.md
│   ├── load-test-basic.js
│   └── load-test-logs.js
├── mdso-alloy/
│   ├── DEPLOYMENT-GUIDE-ENHANCED.md
│   ├── QUICK-START.md
│   ├── README-container.md
│   ├── README.md
│   ├── TEST-GUIDE.md
│   ├── TESTING-GUIDE-ENHANCED.md
│   ├── TESTING-GUIDE.md
│   ├── ask.txt
│   ├── config-test-otel-only.alloy
│   ├── config-test1-pure-otel.alloy
│   ├── config-test2-loki-components.alloy
│   ├── config-test3-full-pipeline.alloy
│   ├── config.alloy
│   ├── deploy-container.sh
│   ├── docker-compose-test.yml
│   ├── docker-compose.yml
│   ├── fix-and-run-test2.sh
│   ├── install.sh
│   ├── charter_sensor_templates/
│   │   ├── .dockerignore
│   │   ├── .flake8
│   │   ├── .gitignore
│   │   ├── .gitlab-ci.yml
│   │   ├── CHANGES.md
│   │   ├── Dockerfile
│   │   ├── Makefile
│   │   ├── README.md
│   │   ├── coverage.json
│   │   ├── pytest.ini
│   │   ├── rp_config.yaml
│   │   ├── service_config.md
│   │   ├── setup.py
│   │   ├── test.xml
│   │   ├── version.json
│   │   ├── docs/
│   │   │   ├── ARDA_Model_Example.json
│   │   │   └── Charter_Sensor_Workflow.gliffy
│   │   ├── external_tools/
│   │   │   └── charter-tools/
│   │   │       ├── Makefile
│   │   │       ├── README.md
│   │   │       ├── charter-tools.py
│   │   │       ├── log_config.ini
│   │   │       └── requirements.txt
│   │   ├── model-definitions/
│   │   │   ├── OTEL_IMPLEMENTATION_SUMMARY.md
│   │   │   ├── README_INSTRUMENTATION.md
│   │   │   ├── __init__.py
│   │   │   ├── requirements_CLIManager.txt
│   │   │   ├── requirements_cpeActivator.txt
│   │   │   ├── requirements_cst.txt
│   │   │   ├── requirements_firmwareUpdater.txt
│   │   │   ├── requirements_managedServicesActivator.txt
│   │   │   ├── requirements_postInstallLightLevels.txt
│   │   │   ├── requirements_scheduler.txt
│   │   │   ├── requirements_seefa.txt
│   │   │   ├── requirements_standaloneconfigdelivery.txt
│   │   │   ├── requirements_turnupLocateIP.txt
│   │   │   ├── scripts.d/
│   │   │   │   ├── scripts.CLIManager.toml
│   │   │   │   ├── scripts.cpeActivator.toml
│   │   │   │   ├── scripts.deviceconfiguration.toml
│   │   │   │   ├── scripts.firmwareUpdater.toml
│   │   │   │   ├── scripts.managedServicesActivator.toml
│   │   │   │   ├── scripts.nagiostests.toml
│   │   │   │   ├── scripts.networkservice.toml
│   │   │   │   ├── scripts.portactivation.toml
│   │   │   │   ├── scripts.postInstallLightLevels.toml
│   │   │   │   ├── scripts.seefa.toml
│   │   │   │   ├── scripts.standaloneconfigdelivery.toml
│   │   │   │   ├── scripts.toml
│   │   │   │   └── scripts.turnupLocateIP.toml
│   │   │   └── scripts/
│   │   │       ├── ENVIRONMENT_LOGGER_README.md
│   │   │       ├── __init__.py
│   │   │       ├── circuitDetailsHandler.py
│   │   │       ├── common_plan.py
│   │   │       ├── complete_and_terminate_plan.py
│   │   │       ├── environment_logger.py
│   │   │       ├── networkserviceupdatevalidate.py
│   │   │       ├── CLIManager/
│   │   │       │   ├── CLIManager.py
│   │   │       │   └── __init__.py
│   │   │       ├── autoActivation/
│   │   │       │   └── postInstallLightLevels/
│   │   │       │       ├── __init__.py
│   │   │       │       └── postInstallLightLevels.py
│   │   │       ├── configmodeler/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── adva.py
│   │   │       │   ├── base.py
│   │   │       │   ├── cisco.py
│   │   │       │   ├── juniper.py
│   │   │       │   ├── modeler.py
│   │   │       │   ├── nokia.py
│   │   │       │   ├── rad.py
│   │   │       │   └── utils.py
│   │   │       ├── cpeIpProvider/
│   │   │       │   ├── __init__.py
│   │   │       │   └── cpeIpProvider.py
│   │   │       ├── deviceReset/
│   │   │       │   ├── advaReset.py
│   │   │       │   ├── base.py
│   │   │       │   ├── deviceReset.py
│   │   │       │   ├── juniperReset.py
│   │   │       │   ├── nokiaReset.py
│   │   │       │   └── radReset.py
│   │   │       ├── deviceconfiguration/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── cli_cutthrough.py
│   │   │       │   ├── deviceconnectivitycheck.py
│   │   │       │   └── deviceonboarder.py
│   │   │       ├── fabricator/
│   │   │       │   ├── common.py
│   │   │       │   ├── compliance.py
│   │   │       │   └── provisioning.py
│   │   │       ├── firmwareUpdater/
│   │   │       │   ├── __init__.py
│   │   │       │   └── firmwareUpdater.py
│   │   │       ├── managedServicesActivator/
│   │   │       │   ├── RPHYAcceptance.py
│   │   │       │   ├── RPHYFWupgrade.py
│   │   │       │   ├── __init__.py
│   │   │       │   ├── customer.py
│   │   │       │   ├── datastore.py
│   │   │       │   ├── managedRPHY.py
│   │   │       │   ├── managedRouterFirmwareUpdater.py
│   │   │       │   ├── managedRouterFirmwareValidator.py
│   │   │       │   ├── managedRouterServicesActivator.py
│   │   │       │   ├── managedSecurityServices.py
│   │   │       │   ├── managedServicesActivator.py
│   │   │       │   ├── ene/
│   │   │       │   │   ├── addresses.py
│   │   │       │   │   ├── api_user.py
│   │   │       │   │   ├── cli_scripts.py
│   │   │       │   │   ├── destination_nat.py
│   │   │       │   │   ├── ene_activator.py
│   │   │       │   │   ├── firewall_policies.py
│   │   │       │   │   ├── interfaces.py
│   │   │       │   │   ├── onboard.py
│   │   │       │   │   ├── routing.py
│   │   │       │   │   ├── services.py
│   │   │       │   │   ├── upgrade_firmware.py
│   │   │       │   │   ├── users.py
│   │   │       │   │   ├── webfilter.py
│   │   │       │   │   └── utilities/
│   │   │       │   │       ├── ene_logger.py
│   │   │       │   │       ├── forticare3.py
│   │   │       │   │       ├── forticloud.py
│   │   │       │   │       ├── fortigateAPI.py
│   │   │       │   │       ├── geography.py
│   │   │       │   │       ├── ssh_connection.py
│   │   │       │   │       ├── utilities.py
│   │   │       │   │       ├── webfilter.py
│   │   │       │   │       └── fsm_templates/
│   │   │       │   │           ├── exe_api_user_generate_key.fsm
│   │   │       │   │           ├── get_system_status.fsm
│   │   │       │   │           ├── index
│   │   │       │   │           ├── show_system_accprofile.fsm
│   │   │       │   │           ├── show_system_admin.fsm
│   │   │       │   │           └── show_system_api_user.fsm
│   │   │       │   ├── fortinet/
│   │   │       │   │   ├── __init__.py
│   │   │       │   │   ├── managedServicesFortiAnalyzer.py
│   │   │       │   │   ├── managedServicesFortiManager.py
│   │   │       │   │   └── managedServicesFortiPortal.py
│   │   │       │   └── merakiServices/
│   │   │       │       ├── MerakiAcceptance.py
│   │   │       │       ├── MerakiClaimDevice.py
│   │   │       │       ├── MerakiCompliance.py
│   │   │       │       ├── __init__.py
│   │   │       │       ├── merakiServices.py
│   │   │       │       ├── merakidashboard.py
│   │   │       │       ├── template_creator.py
│   │   │       │       └── updateLocation.py
│   │   │       ├── multiLeg/
│   │   │       │   └── multilegcircuit.py
│   │   │       ├── nagiostests/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── nagiostests.py
│   │   │       │   └── update_results.py
│   │   │       ├── networkservice/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── businesslogic.py
│   │   │       │   ├── circuitdetailscollector.py
│   │   │       │   ├── cpedeviceconfigvalidator.py
│   │   │       │   ├── create_fre.py
│   │   │       │   ├── networkservice.py
│   │   │       │   ├── networkservicecheck.py
│   │   │       │   ├── networkservicecleaner.py
│   │   │       │   ├── pedeviceconfigvalidator.py
│   │   │       │   ├── peprovisioner.py
│   │   │       │   ├── resourceterminator.py
│   │   │       │   ├── servicedependencymodifier.py
│   │   │       │   ├── servicedevicecvalidator.py
│   │   │       │   ├── servicedeviceonboarder.py
│   │   │       │   ├── servicedeviceprofileconfigurator.py
│   │   │       │   ├── serviceelanprovisioner.py
│   │   │       │   ├── servicefiaprovisioner.py
│   │   │       │   ├── servicefreonboarder.py
│   │   │       │   ├── serviceprovisioner.py
│   │   │       │   ├── softterminate.py
│   │   │       │   ├── status_updater.py
│   │   │       │   ├── update_site_state.py
│   │   │       │   └── updateobservedproperty.py
│   │   │       ├── networkservicedelete/
│   │   │       │   ├── __init__.py
│   │   │       │   └── networkservicedelete.py
│   │   │       ├── networkserviceupdate/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── bandwidth_update.py
│   │   │       │   ├── description_update.py
│   │   │       │   ├── ip_update.py
│   │   │       │   ├── networkserviceupdate.py
│   │   │       │   └── state_toggle.py
│   │   │       └── otel/
│   │   │           ├── CODE_ANALYSIS.md
│   │   │           ├── DIAGNOSTIC_GUIDE.md
│   │   │           ├── feature_flags.py
│   │   │           ├── instrumentation.py
│   │   │           ├── metrics.py
│   │   │           ├── otel_mdso_utils.py
│   │   │           ├── otel_mixin.py
│   │   │           └── requirements.txt
│   │   ├── resources/
│   │   │   └── tests/
│   │   │       ├── README.md
│   │   │       ├── load_paths.py
│   │   │       ├── mockfunctions.py
│   │   │       ├── test_bussinesslogic.py
│   │   │       ├── test_cdc.py
│   │   │       ├── test_common.py
│   │   │       ├── test_networkservice.py
│   │   │       └── jsons/
│   │   │           ├── test_business_logic/
│   │   │           │   ├── input_add_connection_type_to_name.json
│   │   │           │   ├── input_apply_desc_to_interfaces.json
│   │   │           │   ├── input_apply_desc_to_service_endpoints.json
│   │   │           │   ├── input_convert_rad_port_name.json
│   │   │           │   ├── input_convert_variable_names.json
│   │   │           │   ├── input_handle_fia_section.json
│   │   │           │   ├── input_remove_empty_lag_members.json
│   │   │           │   ├── input_replace_ports_with_lags_service_endpoints.json
│   │   │           │   ├── output_add_connection_type_to_name.json
│   │   │           │   ├── output_apply_desc_to_interfaces.json
│   │   │           │   ├── output_apply_desc_to_service_endpoints.json
│   │   │           │   ├── output_convert_rad_port_name.json
│   │   │           │   ├── output_convert_variable_names.json
│   │   │           │   ├── output_handle_fia_section.json
│   │   │           │   ├── output_remove_empty_lag_members.json
│   │   │           │   └── output_replace_ports_with_lags_service_endpoints.json
│   │   │           ├── test_cdc/
│   │   │           │   ├── arda_eline.json
│   │   │           │   ├── arda_fia_complete.json
│   │   │           │   ├── arda_fia_only_pe.json
│   │   │           │   ├── arda_fia_pe_agg.json
│   │   │           │   ├── bpo_constants.json
│   │   │           │   ├── eline_circuit_details.json
│   │   │           │   ├── eline_circuit_details_resource.json
│   │   │           │   ├── fia_complete_circuit_details.json
│   │   │           │   ├── fia_complete_resource.json
│   │   │           │   ├── fia_only_pe_circuit_details.json
│   │   │           │   ├── fia_only_pe_resource.json
│   │   │           │   ├── fia_pe_agg_circuit_details.json
│   │   │           │   └── fia_pe_agg_resource.json
│   │   │           ├── test_networkservice/
│   │   │           │   └── circuit_details.json
│   │   │           ├── test_ns/
│   │   │           │   ├── dependencies.json
│   │   │           │   └── really_good.json
│   │   │           └── test_port_activation/
│   │   │               ├── get-interface.json
│   │   │               ├── tpe.json
│   │   │               └── tpe_up.json
│   │   └── scripts/
│   │       ├── README.md
│   │       ├── update_system_checks.py
│   │       └── tests/
│   │           ├── __init__.py
│   └── mdso-instrumentation/
│       ├── FINDING_PRODUCTS.md
│       ├── IMPLEMENTATION_EXAMPLES.md
│       ├── IMPLEMENTATION_GUIDE.md
│       ├── PRODUCTS_FOUND.md
│       ├── PRODUCT_LOCATION_ANALYSIS.md
│       ├── PRODUCT_LOCATION_SUMMARY.md
│       ├── QUICK_START.md
│       ├── STRATEGY_REVIEW.md
│       ├── TESTING_GUIDE.md
│       ├── USAGE_EXAMPLES.md
│       ├── alloy/
│       │   └── install-alloy.sh
│       └── tests/
│           └── test_otel_mixin.py
├── observability-stack/
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── dashboards/
│   │       │   ├── correlation-overview.json
│   │       │   ├── dashboards.yml
│   │       │   └── trace-logs-correlation.json
│   │       └── datasources/
│   │           └── datasources.yml
│   ├── loki/
│   │   └── loki-config.yaml
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── tempo/
│       └── tempo-config.yaml
├── ops/
│   ├── health-checks.sh
│   ├── logrotate.conf
│   ├── migrate-repo-structure.sh
│   ├── populate-artifacts.sh
│   ├── setup-new-structure.sh
│   ├── stress-test.sh
│   ├── test-traffic.sh
│   ├── gitlab-ci/
│   │   └── .gitlab-ci.yml
│   └── nginx/
│       ├── README.md
│       ├── SERVICE-STARTUP-CONFIGS.md
│       ├── current-nginx-conf.conf
│       ├── nginx-docker-compose.yml
│       ├── nginx-routing-fixes.conf
│       ├── nginx.txt
│       └── ssl/
│           └── ngnix.txt
├── scripts/
│   ├── FIX_NOW.sh
│   ├── SERVER_COMMANDS.sh
│   ├── bootstrap.sh
│   ├── check-selenium.sh
│   ├── cleanup-dev.sh
│   ├── cleanup.sh
│   ├── generate-certs.sh
│   ├── health-check.sh
│   ├── pre-setup.sh
│   ├── query-loki.sh
│   ├── quick-test.sh
│   ├── send-test-span.py
│   ├── setup-server-124.sh
│   ├── setup.md
│   ├── test-connection.sh
│   └── troubleshoot.sh
└── sense-apps/
    ├── .env.example
    ├── DEPLOYMENT.md
    ├── OTEL_INSTRUMENTATION_ANALYSIS.md
    ├── arda/
    │   ├── .coveragerc
    │   ├── .cz.yaml
    │   ├── .env.example
    │   ├── .flake8
    │   ├── .flake8-test
    │   ├── .gitmodules
    │   ├── .pre-commit-config.yaml
    │   ├── CHANGELOG.md
    │   ├── Dockerfile
    │   ├── README.rst
    │   ├── VERSION
    │   ├── debug_logging_settings.json
    │   ├── docker-compose.yml
    │   ├── gunicorn.conf.py
    │   ├── prod_logging_settings.json
    │   ├── pytest.ini
    │   ├── requirements.txt
    │   ├── ruff.toml
    │   ├── run.py
    │   ├── arda_app/
    │   │   ├── __init__.py
    │   │   ├── config.py
    │   │   ├── config_demo.py
    │   │   ├── error_handler.py
    │   │   ├── main.py
    │   │   ├── version.py
    │   │   ├── api/
    │   │   │   ├── __init__.py
    │   │   │   ├── _routers.py
    │   │   │   ├── adva_rad_by_year.py
    │   │   │   ├── assign_enni.py
    │   │   │   ├── assign_evc.py
    │   │   │   ├── assign_gsip.py
    │   │   │   ├── assign_handoffs_and_uplinks.py
    │   │   │   ├── assign_parent_paths.py
    │   │   │   ├── bandwidth_change.py
    │   │   │   ├── blacklist_check.py
    │   │   │   ├── build_circuit_design.py
    │   │   │   ├── check_ip_on_network.py
    │   │   │   ├── circuit_design.py
    │   │   │   ├── circuitpath.py
    │   │   │   ├── cpe_swap.py
    │   │   │   ├── create_bom.py
    │   │   │   ├── create_mtu_transport.py
    │   │   │   ├── create_shelf.py
    │   │   │   ├── customer.py
    │   │   │   ├── design_validation.py
    │   │   │   ├── device.py
    │   │   │   ├── disconnect.py
    │   │   │   ├── elan_add_vpls.py
    │   │   │   ├── exit_criteria.py
    │   │   │   ├── expo_order_processing.py
    │   │   │   ├── health.py
    │   │   │   ├── ip_reclamation.py
    │   │   │   ├── ip_reservation.py
    │   │   │   ├── ip_reservation_gather.py
    │   │   │   ├── ip_swip.py
    │   │   │   ├── ipc_container.py
    │   │   │   ├── ipc_reset.py
    │   │   │   ├── isp_update_related_circuits.py
    │   │   │   ├── ispgroup.py
    │   │   │   ├── light_test_check.py
    │   │   │   ├── logical_change.py
    │   │   │   ├── meraki_services.py
    │   │   │   ├── mock.py
    │   │   │   ├── noc_analysis.py
    │   │   │   ├── optic_check.py
    │   │   │   ├── overlay_design.py
    │   │   │   ├── pick_sova_wo.py
    │   │   │   ├── qc_transport_path.py
    │   │   │   ├── reclaim_cpe_mgmt_ip.py
    │   │   │   ├── related_sitename.py
    │   │   │   ├── remedyticket.py
    │   │   │   ├── service_product_eligibility.py
    │   │   │   ├── serviceable_shelf.py
    │   │   │   ├── site.py
    │   │   │   ├── supported_product.py
    │   │   │   ├── transport_path.py
    │   │   │   ├── type_2_hub_work.py
    │   │   │   ├── type_2_outer_vlan_request.py
    │   │   │   ├── update_path_status.py
    │   │   │   ├── vlan_reservation.py
    │   │   │   └── atlas/
    │   │   │       ├── __init__.py
    │   │   │       ├── accessibility.py
    │   │   │       ├── snmp.py
    │   │   │       └── juniper/
    │   │   │           ├── __init__.py
    │   │   │           └── interface_config.py
    │   │   ├── bll/
    │   │   │   ├── __init__.py
    │   │   │   ├── add_buy_nni.py
    │   │   │   ├── all_products.py
    │   │   │   ├── circuit_status.py
    │   │   │   ├── determine_bom.py
    │   │   │   ├── disconnect.py
    │   │   │   ├── disconnect_utils.py
    │   │   │   ├── expo_order_processing_main.py
    │   │   │   ├── light_test_check.py
    │   │   │   ├── logical_change.py
    │   │   │   ├── nova_to_sova.py
    │   │   │   ├── optic_check.py
    │   │   │   ├── scrape_ip.py
    │   │   │   ├── serviceable_shelf.py
    │   │   │   ├── transport_path.py
    │   │   │   ├── type_2_hub_work.py
    │   │   │   ├── type_two_segment_ops.py
    │   │   │   ├── type_two_transport_path.py
    │   │   │   ├── utils.py
    │   │   │   ├── assign/
    │   │   │   │   ├── enni.py
    │   │   │   │   ├── enni_utils.py
    │   │   │   │   ├── evc.py
    │   │   │   │   ├── gsip.py
    │   │   │   │   ├── relationship.py
    │   │   │   │   └── vpls.py
    │   │   │   ├── atlas/
    │   │   │   │   ├── adva.py
    │   │   │   │   ├── juniper.py
    │   │   │   │   └── snmp.py
    │   │   │   ├── cid/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── cid_globals.py
    │   │   │   │   ├── customer.py
    │   │   │   │   ├── lata_codes.py
    │   │   │   │   ├── pathid.py
    │   │   │   │   └── site.py
    │   │   │   ├── circuit_design/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── bh_mapping.py
    │   │   │   │   ├── circuit_design_main.py
    │   │   │   │   ├── common.py
    │   │   │   │   ├── exit_criteria.py
    │   │   │   │   └── bandwidth_change/
    │   │   │   │       ├── bw_change_main.py
    │   │   │   │       ├── bw_downgrade.py
    │   │   │   │       ├── express_bw_upgrade.py
    │   │   │   │       ├── normal_bw_upgrade.py
    │   │   │   │       └── utils/
    │   │   │   │           ├── granite_util.py
    │   │   │   │           └── network_utils.py
    │   │   │   ├── cpe_swap/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── cpe_swap_constants.py
    │   │   │   │   ├── cpe_swap_main.py
    │   │   │   │   └── cpe_swap_utils.py
    │   │   │   ├── models/
    │   │   │   │   ├── utils.py
    │   │   │   │   ├── device_topology/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── overlay.py
    │   │   │   │   │   └── underlay.py
    │   │   │   │   ├── granite/
    │   │   │   │   │   └── path_elements_model.py
    │   │   │   │   ├── payloads/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── assign_enni.py
    │   │   │   │   │   ├── assign_evc.py
    │   │   │   │   │   ├── assign_gsip.py
    │   │   │   │   │   ├── assign_handoffs_and_uplinks.py
    │   │   │   │   │   ├── assign_parent_paths.py
    │   │   │   │   │   ├── bandwidth_change.py
    │   │   │   │   │   ├── basemodels.py
    │   │   │   │   │   ├── build_circuit_design.py
    │   │   │   │   │   ├── circuit_design.py
    │   │   │   │   │   ├── circuitpath.py
    │   │   │   │   │   ├── cpe_swap.py
    │   │   │   │   │   ├── create_bom.py
    │   │   │   │   │   ├── create_mtu_transport.py
    │   │   │   │   │   ├── create_shelf.py
    │   │   │   │   │   ├── customer.py
    │   │   │   │   │   ├── design_validation.py
    │   │   │   │   │   ├── disconnect.py
    │   │   │   │   │   ├── elan_add_vpls.py
    │   │   │   │   │   ├── exit_criteria.py
    │   │   │   │   │   ├── expo_order_processing.py
    │   │   │   │   │   ├── ip.py
    │   │   │   │   │   ├── ip_reclamation.py
    │   │   │   │   │   ├── ip_reservation.py
    │   │   │   │   │   ├── ip_swip.py
    │   │   │   │   │   ├── ipc_reclaim.py
    │   │   │   │   │   ├── isp_update_related_circuits.py
    │   │   │   │   │   ├── logical_change.py
    │   │   │   │   │   ├── meraki_services.py
    │   │   │   │   │   ├── noc_analysis.py
    │   │   │   │   │   ├── optic_check.py
    │   │   │   │   │   ├── overlay_design.py
    │   │   │   │   │   ├── pick_sova_wo.py
    │   │   │   │   │   ├── qc_transport_path.py
    │   │   │   │   │   ├── related_sitename.py
    │   │   │   │   │   ├── remedy_ticket.py
    │   │   │   │   │   ├── serviceable_shelf.py
    │   │   │   │   │   ├── site.py
    │   │   │   │   │   ├── transport_path.py
    │   │   │   │   │   ├── type_2_hub_work.py
    │   │   │   │   │   ├── update_path_status.py
    │   │   │   │   │   └── vlan_reservation.py
    │   │   │   │   └── responses/
    │   │   │   │       ├── __init__.py
    │   │   │   │       ├── adva_rad.py
    │   │   │   │       ├── all_products.py
    │   │   │   │       ├── assign_enni.py
    │   │   │   │       ├── assign_evc.py
    │   │   │   │       ├── assign_gsip.py
    │   │   │   │       ├── assign_handoffs_and_uplinks.py
    │   │   │   │       ├── assign_parent_paths.py
    │   │   │   │       ├── bandwidth_change.py
    │   │   │   │       ├── blacklist_check.py
    │   │   │   │       ├── build_circuit_design.py
    │   │   │   │       ├── circuit_design.py
    │   │   │   │       ├── circuitpath.py
    │   │   │   │       ├── cpe_swap.py
    │   │   │   │       ├── create_mtu_transport.py
    │   │   │   │       ├── create_shelf.py
    │   │   │   │       ├── customer.py
    │   │   │   │       ├── design_validation.py
    │   │   │   │       ├── device.py
    │   │   │   │       ├── disconnect.py
    │   │   │   │       ├── exit_criteria.py
    │   │   │   │       ├── health.py
    │   │   │   │       ├── ip.py
    │   │   │   │       ├── ip_reclamation.py
    │   │   │   │       ├── ip_reservation.py
    │   │   │   │       ├── ip_swip.py
    │   │   │   │       ├── isp_group.py
    │   │   │   │       ├── light_test_check.py
    │   │   │   │       ├── logical_change.py
    │   │   │   │       ├── meraki_services.py
    │   │   │   │       ├── mock.py
    │   │   │   │       ├── noc_analysis.py
    │   │   │   │       ├── optic_check.py
    │   │   │   │       ├── qc_transport_path.py
    │   │   │   │       ├── reclaim_cpe_mgmt_ip.py
    │   │   │   │       ├── remedy_ticket.py
    │   │   │   │       ├── service_product_eligibility.py
    │   │   │   │       ├── serviceable_shelf.py
    │   │   │   │       ├── site.py
    │   │   │   │       ├── supported_product.py
    │   │   │   │       ├── transport_path.py
    │   │   │   │       ├── update_path_status.py
    │   │   │   │       └── vlan_reservation.py
    │   │   │   ├── net_new/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── assign_parent_paths.py
    │   │   │   │   ├── assign_uplinks_and_handoffs.py
    │   │   │   │   ├── create_cpe.py
    │   │   │   │   ├── create_mne.py
    │   │   │   │   ├── create_mtu_transport.py
    │   │   │   │   ├── create_sbb.py
    │   │   │   │   ├── create_shelf.py
    │   │   │   │   ├── create_vgw.py
    │   │   │   │   ├── inni_matrix.py
    │   │   │   │   ├── ip_reclamation.py
    │   │   │   │   ├── ip_swip.py
    │   │   │   │   ├── meraki_services.py
    │   │   │   │   ├── pe_check.py
    │   │   │   │   ├── reachability_check.py
    │   │   │   │   ├── ip_reservation/
    │   │   │   │   │   ├── assign_ip.py
    │   │   │   │   │   ├── ip_models.py
    │   │   │   │   │   ├── ip_reservation_main.py
    │   │   │   │   │   └── utils/
    │   │   │   │   │       ├── granite_utils.py
    │   │   │   │   │       ├── ipc_utils.py
    │   │   │   │   │       ├── mdso_utils.py
    │   │   │   │   │       └── static_ip_utils.py
    │   │   │   │   ├── utils/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── shelf_utils.py
    │   │   │   │   ├── vlan_reservation/
    │   │   │   │   │   ├── collect_vlans.py
    │   │   │   │   │   ├── vlan_reservation_main.py
    │   │   │   │   │   └── vlan_utils.py
    │   │   │   │   └── with_cj/
    │   │   │   │       ├── __init__.py
    │   │   │   │       └── create_mtu.py
    │   │   │   ├── remedy/
    │   │   │   │   ├── remedy_ticket.py
    │   │   │   │   └── remedy_utils.py
    │   │   │   └── smart/
    │   │   │       └── ipc_reclaim.py
    │   │   ├── common/
    │   │   │   ├── __init__.py
    │   │   │   ├── build_circuit_design_template.py
    │   │   │   ├── bw_operations.py
    │   │   │   ├── cd_constants.py
    │   │   │   ├── cd_utils.py
    │   │   │   ├── endpoints.py
    │   │   │   ├── http_auth.py
    │   │   │   ├── logging_setup.py
    │   │   │   ├── npa_operations.py
    │   │   │   ├── products.py
    │   │   │   ├── regres_testing.py
    │   │   │   ├── sf_integration_error_monitoring.py
    │   │   │   ├── sf_success_monitoring.py
    │   │   │   ├── srvc_prod_eligibility_template.py
    │   │   │   ├── supported_prod_template.py
    │   │   │   ├── truck_roll_list.py
    │   │   │   ├── utils.py
    │   │   │   └── otel/
    │   │   │       ├── __init__.py
    │   │   │       ├── bootstrap.py
    │   │   │       ├── config.py
    │   │   │       ├── mdso_patterns.py
    │   │   │       ├── metrics.py
    │   │   │       ├── observability.py
    │   │   │       ├── otel_sense.py
    │   │   │       ├── telemetry.py
    │   │   │       └── instrumentation/
    │   │   │           ├── ardamainv1.py
    │   │   │           └── requirements.txt
    │   │   ├── data/
    │   │   │   ├── zip_npa.json
    │   │   │   ├── BOM_templates/
    │   │   │   │   ├── ADVA108 BOM.xlsx
    │   │   │   │   ├── ADVA114 BOM.xlsx
    │   │   │   │   ├── ADVA114 DC BOM.xlsx
    │   │   │   │   ├── ADVA114 PRO HE AC (dual PS) BOM.xlsx
    │   │   │   │   ├── ADVA114 PRO HE DC (dual PS) BOM.xlsx
    │   │   │   │   ├── ADVA116 PRO H BOM AC.xlsx
    │   │   │   │   ├── ADVA116 PRO H BOM DC.xlsx
    │   │   │   │   ├── HCT_PRI plus Adva114 BOM.xlsx
    │   │   │   │   ├── HCT_SIP plus Adva114 BOM.xlsx
    │   │   │   │   ├── WIA Cradlepoint E100 BOM.xlsx
    │   │   │   │   ├── WIA Cradlepoint W1850 BOM.xlsx
    │   │   │   │   └── WIA Cradlepoint W1855 BOM.xlsx
    │   │   │   └── mock_circuits/
    │   │   │       ├── mc_build_circuit_design.py
    │   │   │       ├── mc_circuit_design.py
    │   │   │       ├── mc_ip_reservation.py
    │   │   │       ├── mc_light_test_check.py
    │   │   │       ├── mc_update_path_status.py
    │   │   │       └── mc_vlan_reservation.py
    │   │   └── dll/
    │   │       ├── __init__.py
    │   │       ├── arin.py
    │   │       ├── blacklist.py
    │   │       ├── denodo.py
    │   │       ├── expo.py
    │   │       ├── granite.py
    │   │       ├── ipc.py
    │   │       ├── mdso.py
    │   │       ├── remedy.py
    │   │       ├── salesforce.py
    │   │       ├── sense.py
    │   │       ├── thor.py
    │   │       └── utils.py
    │   ├── cicd/
    │   │   ├── deploy.yml
    │   │   ├── qc.yml
    │   │   ├── scan.yml
    │   │   └── test.yml
    │   ├── common_sense/
    │   │   ├── .cz.yaml
    │   │   ├── .gitignore
    │   │   ├── .gitlab-ci.yml
    │   │   ├── CHANGELOG.md
    │   │   ├── README.rst
    │   │   ├── VERSION
    │   │   ├── requirements.txt
    │   │   ├── cicd/
    │   │   │   ├── build_image.yml
    │   │   │   ├── bump_version.yml
    │   │   │   ├── bump_version_common.yml
    │   │   │   ├── bump_version_stage.yml
    │   │   │   ├── qc.yml
    │   │   │   ├── qc_v2.yml
    │   │   │   ├── scan.yml
    │   │   │   ├── ssh_keyscan.yml
    │   │   │   └── test.yml
    │   │   ├── common/
    │   │   │   ├── __init__.py
    │   │   │   ├── api.py
    │   │   │   ├── device.py
    │   │   │   ├── errors.py
    │   │   │   ├── network_devices.py
    │   │   │   ├── summary_mapping_tables.py
    │   │   │   ├── test.py
    │   │   │   └── utils.py
    │   │   ├── dll/
    │   │   │   ├── __init__.py
    │   │   │   ├── auth.py
    │   │   │   ├── device_snmp.py
    │   │   │   ├── hydra.py
    │   │   │   ├── sense.py
    │   │   │   └── snmp.py
    │   │   └── tests/
    │   │       ├── __init__.py
    │   │       └── test_snmp.py
    │   ├── logs/
    │   │   └── README.md
    │   ├── mock_data/
    │   │   ├── __init__.py
    │   │   ├── cans_cid.json
    │   │   ├── cans_cid.xml
    │   │   ├── cans_cid_get_resp.json
    │   │   ├── cans_tid.json
    │   │   ├── cans_tid.xml
    │   │   ├── cans_tid_get_resp.json
    │   │   ├── cid_creation.json
    │   │   ├── eline.json
    │   │   ├── mock_npa_valid_response.json
    │   │   ├── mock_post_granite.json
    │   │   ├── v1_topologies_test_001461.json
    │   │   ├── v1_topologies_test_814265.json
    │   │   ├── v2_topologies_test_001461.json
    │   │   ├── circuit_design/
    │   │   │   ├── __init__.py
    │   │   │   ├── circuit_upgrade.py
    │   │   │   ├── device_mock_data.py
    │   │   │   └── net_new/
    │   │   │       ├── circuit_upgrade/
    │   │   │       │   └── data.py
    │   │   │       ├── ip_swip/
    │   │   │       │   └── data.py
    │   │   │       ├── static_ip_assignment/
    │   │   │       │   └── static_ip_mock_data.py
    │   │   │       └── vlan/
    │   │   │           └── data.py
    │   │   └── common/
    │   │       └── Adonis/
    │   │           ├── data.py
    │   │           └── data_v2.py
    │   ├── public/
    │   │   ├── index.html
    │   │   └── sense.ico
    │   └── tests/
    │       ├── __init__.py
    │       ├── conftest.py
    │       ├── test_bw_operations.py
    │       ├── test_check_ip_on_network.py
    │       ├── test_circuit_design.py
    │       ├── test_cpe_swap_main.py
    │       ├── test_create_bom.py
    │       ├── test_create_cpe.py
    │       ├── test_express_bw_upgrade.py
    │       ├── test_ip_reclamation.py
    │       ├── test_ipc_container.py
    │       ├── test_light_test_check.py
    │       ├── test_logical_change.py
    │       ├── test_normal_bw_upgrade.py
    │       ├── test_optic_validation.py
    │       ├── test_pick_sova_wo.py
    │       ├── test_transport_path.py
    │       ├── test_update_related_circuits.py
    │       ├── test_utils.py
    │       ├── test_vlan_reservation.py
    │       ├── test_wavelength.py
    │       ├── data/
    │       │   ├── __init__.py
    │       │   ├── device_validator_data.py
    │       │   ├── downgrade_rev_create_good.json
    │       │   ├── granite_query.csv
    │       │   ├── optic_validation_data.py
    │       │   ├── path_creation_two_sites.json
    │       │   ├── transport_operations_data.py
    │       │   ├── transport_path_data.py
    │       │   ├── update_related_circuits_data.py
    │       │   └── wavelength_data.py
    │       ├── test_assign/
    │       │   ├── test_assign_enni.py
    │       │   ├── test_assign_evc.py
    │       │   ├── test_assign_gsip.py
    │       │   └── test_assign_vpls.py
    │       ├── test_cid_creation/
    │       │   ├── __init__.py
    │       │   ├── test_cid_creation_mock_functions.py
    │       │   ├── test_customer.py
    │       │   ├── test_path_creation.py
    │       │   ├── test_pathid_operations.py
    │       │   ├── test_related_sitename.py
    │       │   ├── test_site.py
    │       │   ├── test_site_selection.py
    │       │   └── test_utils.py
    │       ├── test_circuit_design/
    │       │   ├── test_device.py
    │       │   └── test_net_new/
    │       │       ├── __init__.py
    │       │       ├── test_assign_handoffs_and_uplinks.py
    │       │       ├── test_assign_parent_paths.py
    │       │       ├── test_build_circuit_design.py
    │       │       ├── test_build_circuit_design_template.py
    │       │       ├── test_circuit_design.py
    │       │       ├── test_circuit_status.py
    │       │       ├── test_create_mtu.py
    │       │       ├── test_create_mtu_transport.py
    │       │       ├── test_create_shelf.py
    │       │       ├── test_create_vgw.py
    │       │       ├── test_disconnect.py
    │       │       ├── test_exit_criteria.py
    │       │       ├── test_ip_reservation.py
    │       │       ├── test_ip_swip.py
    │       │       ├── test_meraki_services.py
    │       │       ├── test_outer_vlan_reservation_type2.py
    │       │       ├── test_pe_check.py
    │       │       ├── test_service_product_eligibility.py
    │       │       ├── test_serviceable_shelf.py
    │       │       ├── test_shelf_utils.py
    │       │       ├── test_srvc_prod_eligibility_template.py
    │       │       ├── test_supported_product.py
    │       │       ├── test_supported_product_template.py
    │       │       ├── test_type_two.py
    │       │       ├── test_type_two_segment.py
    │       │       └── test_vlan_reservation.py
    │       ├── test_common/
    │       │   ├── __init__.py
    │       │   ├── test_arda.py
    │       │   ├── test_common.py
    │       │   ├── test_design_utils.py
    │       │   ├── test_disconnect_globals.py
    │       │   ├── test_granite.py
    │       │   ├── test_ipc_operations.py
    │       │   ├── test_logging.py
    │       │   └── test_sense.py
    │       └── test_design_tools/
    │           └── test_ip_reservation_gather.py
    └── beorn/
        ├── .cz.yaml
        ├── .env.example
        ├── .flake8
        ├── .flake8-test
        ├── .gitignore
        ├── .gitmodules
        ├── .pre-commit-config.yaml
        ├── CHANGELOG.md
        ├── Dockerfile
        ├── README.rst
        ├── VERSION
        ├── debug_logging_settings.json
        ├── gunicorn.conf.py
        ├── instrumentation_helpers.py
        ├── prod_logging_settings.json
        ├── pyproject.toml
        ├── pytest.ini
        ├── requirements.txt
        ├── run.py
        ├── beorn_app/
        │   ├── __init__.py
        │   ├── config.py
        │   ├── config_demo.py
        │   ├── instrumentation_helpers.py
        │   ├── apis/
        │   │   ├── __init__.py
        │   │   ├── v1/
        │   │   │   ├── __init__.py
        │   │   │   ├── bandwidth.py
        │   │   │   ├── cpe.py
        │   │   │   ├── device.py
        │   │   │   ├── eligibility.py
        │   │   │   ├── ene.py
        │   │   │   ├── granite_status.py
        │   │   │   ├── health.py
        │   │   │   ├── managed_rphy.py
        │   │   │   ├── managed_service.py
        │   │   │   ├── mne.py
        │   │   │   ├── rphy_rfcodes.py
        │   │   │   ├── service.py
        │   │   │   └── submodule_test.py
        │   │   ├── v2/
        │   │   │   ├── __init__.py
        │   │   │   ├── cpe.py
        │   │   │   ├── eligibility.py
        │   │   │   └── managed_service.py
        │   │   └── v3/
        │   │       ├── __init__.py
        │   │       ├── cpe.py
        │   │       ├── service.py
        │   │       └── topologies.py
        │   ├── bll/
        │   │   ├── __init__.py
        │   │   ├── cpe.py
        │   │   ├── ene.py
        │   │   ├── eset.py
        │   │   ├── granite.py
        │   │   ├── ip_finder.py
        │   │   ├── managed_rphy.py
        │   │   ├── managed_service.py
        │   │   ├── mne.py
        │   │   ├── service.py
        │   │   ├── snmp.py
        │   │   ├── topologies.py
        │   │   └── eligibility/
        │   │       ├── automation_eligibility.py
        │   │       ├── circuit_test.py
        │   │       ├── circuit_test_eligibility.py
        │   │       ├── mdso_eligible.py
        │   │       ├── rphy_activation_eligibility.py
        │   │       ├── compliance/
        │   │       │   ├── change_compliance.py
        │   │       │   ├── disco_compliance.py
        │   │       │   └── new_compliance.py
        │   │       └── provisioning/
        │   │           ├── change_provisioning.py
        │   │           └── new_provisioning.py
        │   ├── common/
        │   │   ├── DLLcallResult.py
        │   │   ├── __init__.py
        │   │   ├── auth.py
        │   │   ├── endpoints.py
        │   │   ├── generic.py
        │   │   ├── granite_operations.py
        │   │   ├── http_auth.py
        │   │   ├── kafka_operation.py
        │   │   ├── logging_setup.py
        │   │   ├── mdso_auth.py
        │   │   ├── mdso_operations.py
        │   │   ├── regres_testing.py
        │   │   ├── sense_operations.py
        │   │   ├── utils.py
        │   │   └── otel/
        │   │       ├── __init__.py
        │   │       ├── bootstrap.py
        │   │       ├── config.py
        │   │       ├── mdso_patterns.py
        │   │       ├── metrics.py
        │   │       ├── observability.py
        │   │       ├── otel_sense.py
        │   │       ├── telemetry.py
        │   │       └── instrumentation/
        │   │           ├── arda_main.py
        │   │           └── requirements.txt
        │   └── dll/
        │       ├── __init__.py
        │       ├── denodo.py
        │       ├── eset.py
        │       ├── granite.py
        │       ├── hydra.py
        │       ├── ipc.py
        │       ├── mdso.py
        │       ├── sales_force.py
        │       ├── sense.py
        │       └── snmp.py
        ├── cicd/
        │   ├── deploy.yml
        │   ├── qc.yml
        │   ├── scan.yml
        │   └── test.yml
        ├── common_sense/
        │   ├── .cz.yaml
        │   ├── .gitignore
        │   ├── .gitlab-ci.yml
        │   ├── CHANGELOG.md
        │   ├── README.rst
        │   ├── VERSION
        │   ├── requirements.txt
        │   ├── cicd/
        │   │   ├── build_image.yml
        │   │   ├── bump_version.yml
        │   │   ├── bump_version_common.yml
        │   │   ├── bump_version_stage.yml
        │   │   ├── qc.yml
        │   │   ├── qc_v2.yml
        │   │   ├── scan.yml
        │   │   ├── ssh_keyscan.yml
        │   │   └── test.yml
        │   ├── common/
        │   │   ├── __init__.py
        │   │   ├── api.py
        │   │   ├── device.py
        │   │   ├── errors.py
        │   │   ├── network_devices.py
        │   │   ├── summary_mapping_tables.py
        │   │   ├── test.py
        │   │   └── utils.py
        │   ├── dll/
        │   │   ├── __init__.py
        │   │   ├── auth.py
        │   │   ├── device_snmp.py
        │   │   ├── hydra.py
        │   │   ├── sense.py
        │   │   └── snmp.py
        │   └── tests/
        │       ├── __init__.py
        │       └── test_snmp.py
        ├── logs/
        │   └── README.md
        └── tests/
            ├── __init__.py
            ├── conftest.py
            ├── mock_data/
            │   ├── __init__.py
            │   ├── circuit_testing/  [20 JSON files]
            │   ├── compliance/
            │   │   ├── elan1_slm_eligible_circuit_uda.json
            │   │   ├── elan1_slm_eligible_denodo.json
            │   │   ├── elan1_slm_eligible_granite.json
            │   │   ├── elan2_slm_ineligible_circuit_uda.json
            │   │   ├── elan2_slm_ineligible_denodo.json
            │   │   ├── elan2_slm_ineligible_granite.json
            │   │   ├── pre_mdso_check_data.py
            │   │   └── topologies.py
            │   ├── eligibility/  [change/ and new/ subdirs]
            │   ├── hydra/
            │   │   └── dv_dice_topology_v5/  [4 JSON files]
            │   ├── managed_services/
            │   │   ├── v1products_post_to_service.json
            │   │   └── v1products_product_query.json
            │   └── topologies/  [~60 JSON files]
            └── [test_*.py files]
```
