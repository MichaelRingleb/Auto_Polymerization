# Medusa Diagnostic Tools

This directory contains comprehensive diagnostic tools for testing medusa's capabilities and identifying issues to report to the medusa development team.

## Overview

The diagnostic tools are designed to:
- **Systematically test** all medusa capabilities
- **Identify specific issues** with reproducible test cases
- **Generate detailed reports** for the medusa development team
- **Provide actionable feedback** for bug fixes and improvements

## Tools Available

### 1. Medusa Diagnostic (`medusa_diagnostic.py`)

Core diagnostic engine that tests:
- Medusa package availability and version
- Layout file validation
- Medusa initialization
- Graph structure analysis
- SerialDevice functionality
- Pump connectivity
- Heat plate functionality
- Peristaltic pump functionality
- UV-VIS integration
- Error handling capabilities

### 2. Developer Report Generator (`run_medusa_diagnostic.py`)

User-friendly interface that:
- Runs comprehensive diagnostics
- Generates detailed JSON reports
- Creates developer-friendly markdown reports
- Provides clear reproduction steps

## Quick Start

### Run Complete Diagnostic

```bash
cd Auto_Polymerization/demo
python run_medusa_diagnostic.py
```

This will:
1. Prompt for your layout file path
2. Run all diagnostic tests
3. Generate two report files:
   - `medusa_diagnostic_report_[timestamp].json` (technical data)
   - `medusa_developer_report_[timestamp].md` (developer-friendly)

### Run Individual Tests

```bash
cd Auto_Polymerization/demo
python medusa_diagnostic.py
```

This provides more control over individual test execution.

## What the Diagnostic Tests

### 1. Medusa Availability Test
- Checks if medusa package is installed
- Verifies import functionality
- Reports version information
- Identifies installation issues

### 2. Layout File Validation
- Validates JSON structure
- Checks file existence and readability
- Analyzes node and link counts
- Identifies SerialDevice configurations

### 3. Medusa Initialization Test
- Tests medusa object creation
- Validates graph loading
- Reports initialization errors
- Provides detailed error traces

### 4. Graph Structure Analysis
- Analyzes node types and counts
- Identifies isolated nodes
- Reports connectivity issues
- Validates graph integrity

### 5. SerialDevice Functionality Test
- Tests `write_serial` method availability
- Validates SerialDevice node configurations
- Identifies communication issues
- Reports specific error types

### 6. Pump Connectivity Test
- Analyzes pump configurations
- Tests `transfer_volumetric` method
- Identifies vessel-pump path issues
- Reports connectivity problems

### 7. Heat Plate Functionality Test
- Analyzes IKAHotplate configurations
- Tests `heat_stir` method availability
- Tests `get_hotplate_temperature` and `get_hotplate_rpm` methods
- Identifies heat plate communication issues
- Reports method availability and signatures

### 8. Peristaltic Pump Functionality Test
- Analyzes LongerPeristalticPump configurations
- Tests `transfer_continuous` method availability
- Identifies peristaltic pump communication issues
- Reports method availability and signatures
- Validates pump-vessel connectivity

### 9. UV-VIS Integration Test
- Tests UV-VIS utility availability
- Validates spectrometer integration
- Reports DLL path issues
- Identifies device connection problems

### 10. Error Handling Test
- Tests error handling for invalid inputs
- Validates exception handling
- Reports error handling gaps
- Identifies potential improvements

## Report Formats

### JSON Report (`medusa_diagnostic_report_[timestamp].json`)

Detailed technical data including:
```json
{
  "timestamp": "2025-01-09 18:46:10",
  "medusa_version": "1.2.3",
  "system_info": {
    "python_version": "3.10.0",
    "platform": "Windows-10-10.0.19045-SP0",
    "architecture": "64bit"
  },
  "tests": {
    "medusa_availability": {
      "success": true,
      "details": {
        "version": "1.2.3",
        "module_path": "/path/to/medusa"
      }
    },
    "serial_device": {
      "success": false,
      "details": {
        "error": "write_serial method not found",
        "error_type": "AttributeError"
      }
    }
  },
  "issues": [
    "SerialDevice functionality not working"
  ],
  "recommendations": [
    "Check medusa SerialDevice implementation"
  ]
}
```

### Markdown Report (`medusa_developer_report_[timestamp].md`)

Developer-friendly format ready for GitHub issues:
```markdown
# Medusa Diagnostic Report for Developers

**Generated:** 2025-01-09 18:46:10
**Medusa Version:** 1.2.3
**Python Version:** 3.10.0
**Platform:** Windows-10-10.0.19045-SP0

## Test Results Summary

- **medusa_availability:** ✅ PASS
- **serial_device:** ❌ FAIL
- **pump_connectivity:** ❌ FAIL

**Overall:** 1/3 tests passed

## Detailed Test Results

### Serial Device

**Status:** ❌ FAIL

**Details:**
- write_serial method not found

**Error:**
```
```