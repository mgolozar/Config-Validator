# Config Validator

Config Validator is a lightweight and extensible framework for validating configuration files across different environments and storage systems.
It’s designed to make large-scale configuration validation fast, maintainable, and observable — all while keeping setup simple.

# Overview

The project supports:

Asynchronous validation with configurable concurrency

Dynamic rule loading via a plugin system

Real-time monitoring and automatic re-validation using Watchdog

Report generation in both JSON and NDJSON formats

Built-in observability through Grafana, Loki, and Promtail

Easy extensibility using Strategy and Decorator design patterns

All core modules are fully type-hinted and tested, ensuring stability and readability.

# Project Structure
src/config_validator/      # Core Python package
tests/                     # Unit and integration tests
ops/observability/         # Grafana, Loki, and Promtail setup
config/                    # Validation and storage configuration
reports/                   # Generated JSON / NDJSON reports
docs/                      # Documentation and references

# Key Features

Decorator-based rule system – Add or modify validation rules by simply applying a decorator.

Async engine – Handles large data sets efficiently using async/await and semaphores.

Watch mode – Tracks file changes in real time for continuous validation.

Dynamic reports – Generates validation summaries and error breakdowns automatically.

Extensible storage – Uses a strategy pattern to support Local, S3, and HDFS backends.

Automatic logging – Decorators make it easy to log the start and end of any process.

Comprehensive testing – Each component includes its own extendable test suite.

# Dashboards

Two Grafana dashboards are included under ops/observability/grafana/dashboards/:

Config Validator – Overview Dashboard
Summarizes validation activity and error distribution across files.

Config Validator – Errors and Trends Dashboard
Visualizes error patterns and trends over time for deeper analysis.

Screenshots and panel descriptions are available inside the PDF documentation.

Setup & Usage
# Install package
pip install config_validator-0.1.0-py3-none-any.whl

# Run validation
make run

# Execute tests
make test

# Start observability stack
cd ops/observability && docker compose up -d

# Technical Documentation

For a detailed explanation of architecture, components, and dashboards,
see ConfigValidator-Feature_and_Architecture_Document.pdf
 inside the docs/ directory.

# License

This project is distributed for internal evaluation and demonstration purposes.
All rights reserved © 2025.
