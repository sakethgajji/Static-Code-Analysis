import os
import subprocess
import json
import datetime
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

def run_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), -1

def analyze_code(target_path="*.py", bandit_target="."):
    print(f"Running Pylint on {target_path}...")
    pylint_out, _, _ = run_command(f"python -m pylint {target_path} --output-format=json")
    
    print(f"Running Flake8 on {target_path}...")
    flake8_out, _, _ = run_command(f"python -m flake8 {target_path}")
    
    print(f"Running Bandit on {bandit_target}...")
    bandit_out, _, _ = run_command(f"python -m bandit -r {bandit_target} -f json")

    # Parse Pylint
    pylint_issues = []
    try:
        if pylint_out.strip():
            pylint_issues = json.loads(pylint_out)
    except Exception as e:
        print(f"Error parsing pylint: {e}")

    # Parse Bandit
    bandit_issues = []
    try:
        if bandit_out.strip():
            bandit_data = json.loads(bandit_out)
            bandit_issues = bandit_data.get('results', [])
    except Exception as e:
        print(f"Error parsing bandit: {e}")

    # Calculate metrics
    errors = len([i for i in pylint_issues if i.get('type') == 'error'])
    warnings = len([i for i in pylint_issues if i.get('type') == 'warning'])
    
    # Flake8 output is one issue per line
    flake8_lines = [line for line in flake8_out.split('\n') if line.strip()]
    warnings += len(flake8_lines)

    security_issues = len(bandit_issues)

    # Simple Quality Score calculation (out of 10)
    # Deduct 0.5 for each error, 0.2 for each warning, 1.0 for each security issue
    score = 10.0 - (errors * 0.5) - (warnings * 0.2) - (security_issues * 1.0)
    quality_score = max(0.0, round(score, 1))

    status = "Passed" if quality_score >= 7.0 and security_issues == 0 else "Failed"

    project_name = os.path.basename(target_path) if target_path != "*.py" else (os.path.basename(os.getcwd()) or "Static-Code-Analysis")
    return {
        "project_name": project_name,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "quality_score": quality_score,
        "errors": errors,
        "warnings": warnings,
        "security_issues": security_issues,
        "status": status,
        "pylint_issues": pylint_issues,
        "flake8_issues": flake8_lines,
        "bandit_issues": bandit_issues
    }

def generate_pdf(metrics, filename="Analysis_Report.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Static Code Analysis Report")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Project: {metrics['project_name']}")
    c.drawString(50, height - 100, f"Date: {metrics['date']}")
    c.drawString(50, height - 120, f"Quality Score: {metrics['quality_score']} / 10")
    c.drawString(50, height - 140, f"Pipeline Status: {metrics['status']}")
    
    c.drawString(50, height - 170, f"Errors: {metrics['errors']}")
    c.drawString(50, height - 190, f"Warnings: {metrics['warnings']}")
    c.drawString(50, height - 210, f"Security Issues: {metrics['security_issues']}")
    
    y = height - 250
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Details:")
    y -= 20
    
    c.setFont("Helvetica", 10)
    
    # Sort issues to put errors/fatals first, then warnings, then others
    severity_order = {'fatal': 0, 'error': 1, 'warning': 2, 'refactor': 3, 'convention': 4}
    sorted_issues = sorted(metrics['pylint_issues'], key=lambda x: severity_order.get(x.get('type', 'convention'), 5))
    
    for issue in sorted_issues[:15]: # Show top 15 prioritized issues
        text = f"Pylint ({issue.get('type')}): {issue.get('path')}:{issue.get('line')} - {issue.get('message')}"
        lines = simpleSplit(text, "Helvetica", 10, width - 100)
        for line in lines:
            c.drawString(50, y, line)
            y -= 12
            if y < 50:
                c.showPage()
                y = height - 50
    
    c.save()
    return filename

def send_webhook(metrics, pdf_path):
    webhook_url = os.getenv("DASHBOARD_WEBHOOK_URL", "http://127.0.0.1:5000/api/webhook")
    print(f"Sending results to {webhook_url}...")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'pdf_report': (pdf_path, f, 'application/pdf')}
            data = {'metrics': json.dumps(metrics)}
            response = requests.post(webhook_url, data=data, files=files)
            
        if response.status_code == 200:
            print("Successfully sent to dashboard.")
        else:
            print(f"Failed to send. Status Code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending webhook: {e}")

if __name__ == "__main__":
    results = analyze_code()
    print(f"Analysis complete. Score: {results['quality_score']}, Status: {results['status']}")
    pdf_file = generate_pdf(results)
    send_webhook(results, pdf_file)
