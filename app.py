from flask import Flask, request, jsonify, render_template, send_file
import os
import json
import database
import ci_analyzer
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'reports'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize DB
database.init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        metrics_data = request.form.get('metrics')
        if not metrics_data:
            return jsonify({"error": "No metrics provided"}), 400
            
        metrics = json.loads(metrics_data)
        
        pdf_file = request.files.get('pdf_report')
        pdf_path = None
        
        if pdf_file and pdf_file.filename != '':
            filename = secure_filename(f"report_{metrics['date'].replace(':', '-')}.pdf")
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(pdf_path)

        report_id = database.insert_report(
            project_name=metrics.get('project_name', 'Unknown'),
            date=metrics.get('date'),
            quality_score=metrics.get('quality_score', 0),
            errors=metrics.get('errors', 0),
            warnings=metrics.get('warnings', 0),
            security_issues=metrics.get('security_issues', 0),
            status=metrics.get('status', 'Unknown'),
            pdf_report_path=pdf_path
        )
        
        return jsonify({"message": "Successfully recorded", "report_id": report_id}), 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze_file', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)
        
        try:
            # Run analysis directly on this file
            results = ci_analyzer.analyze_code(target_path=filepath, bandit_target=filepath)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"report_{results['date'].replace(':', '-')}_{filename}.pdf")
            ci_analyzer.generate_pdf(results, pdf_path)
            
            # Save to DB so it shows up on dashboard
            report_id = database.insert_report(
                project_name=f"File: {filename}",
                date=results['date'],
                quality_score=results['quality_score'],
                errors=results['errors'],
                warnings=results['warnings'],
                security_issues=results['security_issues'],
                status=results['status'],
                pdf_report_path=pdf_path
            )
            
            # Cleanup the temp file
            os.remove(filepath)
            
            return jsonify({"message": "Successfully analyzed", "report_id": report_id}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def history():
    reports = database.get_all_reports()
    return jsonify(reports)

@app.route('/api/download_pdf/<int:report_id>')
def download_pdf(report_id):
    reports = database.get_all_reports()
    report = next((r for r in reports if r['report_id'] == report_id), None)
    
    if report and report.get('pdf_report_path') and os.path.exists(report['pdf_report_path']):
        return send_file(report['pdf_report_path'], as_attachment=True)
    return "PDF not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
