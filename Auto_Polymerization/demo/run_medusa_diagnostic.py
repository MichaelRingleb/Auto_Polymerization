"""
Run Medusa Diagnostic and Generate Developer Report.

This script runs the comprehensive medusa diagnostic and creates
a detailed report for the medusa developers.

Usage:
    python run_medusa_diagnostic.py
"""

import sys
from pathlib import Path
import json
import time

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from demo.medusa_diagnostic import MedusaDiagnostic


def create_developer_report(diagnostic_results: dict) -> str:
    """
    Create a developer-friendly report from diagnostic results.
    
    Args:
        diagnostic_results (dict): Results from medusa diagnostic
        
    Returns:
        str: Formatted report for developers
    """
    report = []
    report.append("# Medusa Diagnostic Report for Developers")
    report.append("")
    report.append(f"**Generated:** {diagnostic_results['timestamp']}")
    report.append(f"**Medusa Version:** {diagnostic_results['medusa_version']}")
    report.append(f"**Python Version:** {diagnostic_results['system_info']['python_version']}")
    report.append(f"**Platform:** {diagnostic_results['system_info']['platform']}")
    report.append("")
    
    # Test Results Summary
    report.append("## Test Results Summary")
    report.append("")
    
    passed_tests = 0
    total_tests = len(diagnostic_results['tests'])
    
    for test_name, test_result in diagnostic_results['tests'].items():
        status = "✅ PASS" if test_result.get("success", False) else "❌ FAIL"
        report.append(f"- **{test_name}:** {status}")
        if test_result.get("success", False):
            passed_tests += 1
    
    report.append("")
    report.append(f"**Overall:** {passed_tests}/{total_tests} tests passed")
    report.append("")
    
    # Detailed Test Results
    report.append("## Detailed Test Results")
    report.append("")
    
    for test_name, test_result in diagnostic_results['tests'].items():
        report.append(f"### {test_name.replace('_', ' ').title()}")
        report.append("")
        
        if test_result.get("success", False):
            report.append("**Status:** ✅ PASS")
        else:
            report.append("**Status:** ❌ FAIL")
        
        report.append("")
        
        # Add details
        details = test_result.get("details", {})
        if details:
            report.append("**Details:**")
            for key, value in details.items():
                if isinstance(value, dict):
                    report.append(f"- {key}:")
                    for sub_key, sub_value in value.items():
                        report.append(f"  - {sub_key}: {sub_value}")
                else:
                    report.append(f"- {key}: {value}")
            report.append("")
        
        # Add error if present
        if "error" in details:
            report.append("**Error:**")
            report.append(f"```")
            report.append(details["error"])
            report.append("```")
            report.append("")
    
    # Issues Found
    if diagnostic_results.get("issues"):
        report.append("## Issues Found")
        report.append("")
        for issue in diagnostic_results["issues"]:
            report.append(f"- {issue}")
        report.append("")
    
    # Recommendations
    if diagnostic_results.get("recommendations"):
        report.append("## Recommendations")
        report.append("")
        for rec in diagnostic_results["recommendations"]:
            report.append(f"- {rec}")
        report.append("")
    
    # Reproduction Steps
    report.append("## Reproduction Steps")
    report.append("")
    report.append("To reproduce these issues:")
    report.append("")
    report.append("1. Install the same environment:")
    report.append(f"   - Python {diagnostic_results['system_info']['python_version']}")
    report.append(f"   - Platform: {diagnostic_results['system_info']['platform']}")
    report.append("")
    report.append("2. Use the provided JSON layout file")
    report.append("")
    report.append("3. Run the diagnostic tool:")
    report.append("   ```bash")
    report.append("   python medusa_diagnostic.py")
    report.append("   ```")
    report.append("")
    
    # Raw Data Reference
    report.append("## Raw Data")
    report.append("")
    report.append("Complete diagnostic data is available in `medusa_diagnostic_report.json`")
    report.append("")
    
    return "\n".join(report)


def main():
    """Main function to run diagnostic and generate report."""
    print("=" * 80)
    print("MEDUSA DIAGNOSTIC FOR DEVELOPERS")
    print("=" * 80)
    print("This will run comprehensive diagnostics and generate a report")
    print("suitable for sharing with the medusa development team.")
    print()
    
    # Get layout file path
    layout_path = input("Enter path to your Medusa design JSON file: ").strip()
    
    if not layout_path:
        print("No layout file provided. Using default path...")
        layout_path = "../users/config/fluidic_design_autopoly.json"
    
    print(f"\nUsing layout file: {layout_path}")
    print("\nStarting comprehensive diagnostics...")
    print("This may take a few minutes...")
    
    # Create and run diagnostic
    diagnostic = MedusaDiagnostic(layout_path)
    results = diagnostic.run_all_diagnostics()
    
    # Save detailed JSON report
    json_filename = f"medusa_diagnostic_report_{int(time.time())}.json"
    diagnostic.save_report(json_filename)
    
    # Create developer-friendly markdown report
    markdown_report = create_developer_report(results)
    markdown_filename = f"medusa_developer_report_{int(time.time())}.md"
    
    with open(markdown_filename, 'w') as f:
        f.write(markdown_report)
    
    # Print summary
    diagnostic.print_summary()
    
    print("\n" + "=" * 80)
    print("REPORTS GENERATED")
    print("=" * 80)
    print(f"📄 Detailed JSON report: {json_filename}")
    print(f"📝 Developer markdown report: {markdown_filename}")
    print()
    print("Please share these files with the medusa development team.")
    print("The markdown report is ready to be posted as a GitHub issue.")
    print("=" * 80)


if __name__ == "__main__":
    main() 