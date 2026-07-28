document.addEventListener('DOMContentLoaded', () => {
    // Dashboard Elements
    const scoreNum = document.getElementById('score-num');
    const gradeBadge = document.getElementById('grade-badge');
    const gradeDesc = document.getElementById('grade-desc');
    const gaugeProgress = document.getElementById('gauge-progress');
    const pipelineStatus = document.getElementById('pipeline-status');

    // Metrics Cards
    const metricProjectName = document.getElementById('metric-project-name');
    const metricLastTime = document.getElementById('metric-last-time');
    const metricWarnings = document.getElementById('metric-warnings');
    const metricErrors = document.getElementById('metric-errors');
    const metricSecurity = document.getElementById('metric-security');

    // History Table
    const historyTbody = document.getElementById('history-tbody');
    
    // Actions
    const btnExportReport = document.getElementById('btn-export-report');
    const btnDownloadPdf = document.getElementById('btn-download-pdf');
    const fileUploadInput = document.getElementById('file-upload-input');
    
    let reports = [];

    // Fetch History
    async function fetchHistory() {
        try {
            const response = await fetch('/api/history');
            if (!response.ok) throw new Error("Failed to fetch history");
            reports = await response.json();
            
            renderHistoryTable();
            if (reports.length > 0) {
                renderDashboard(reports[0]); // Show latest report
            } else {
                pipelineStatus.textContent = "Status: No Analysis Run";
                pipelineStatus.style.borderColor = "var(--text-muted)";
                pipelineStatus.style.color = "var(--text-muted)";
                historyTbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center">No historical data available. Push code to trigger GitHub Actions.</td></tr>';
            }
        } catch (err) {
            console.error(err);
            historyTbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center" style="color:var(--accent-rose)">Error loading history.</td></tr>';
            pipelineStatus.textContent = "Status: Error";
        }
    }

    function renderHistoryTable() {
        if (reports.length === 0) return;
        
        historyTbody.innerHTML = reports.map(r => `
            <tr onclick="window.selectReport(${r.report_id})" style="cursor:pointer" class="history-row">
                <td>${r.date}</td>
                <td><strong>${r.quality_score}</strong></td>
                <td>
                    <span class="badge ${r.status === 'Passed' ? 'bg-green' : 'bg-rose'}" style="padding:4px 8px;border-radius:12px;font-size:0.8rem;background:var(--accent-${r.status === 'Passed' ? 'green' : 'rose'})">
                        ${r.status}
                    </span>
                </td>
                <td>
                    ${r.pdf_report_path ? `<a href="/api/download_pdf/${r.report_id}" class="icon-btn" onclick="event.stopPropagation()" title="Download PDF"><i class="fa-solid fa-file-pdf"></i></a>` : '-'}
                </td>
            </tr>
        `).join('');
    }
    
    window.selectReport = function(id) {
        const report = reports.find(r => r.report_id === id);
        if (report) renderDashboard(report);
    };

    function renderDashboard(report) {
        // Pipeline Status
        pipelineStatus.textContent = `Pipeline: ${report.status}`;
        if (report.status === 'Passed') {
            pipelineStatus.style.borderColor = "var(--accent-green)";
            pipelineStatus.style.color = "var(--accent-green)";
        } else {
            pipelineStatus.style.borderColor = "var(--accent-rose)";
            pipelineStatus.style.color = "var(--accent-rose)";
        }
        
        // Gauge
        scoreNum.textContent = report.quality_score;
        let grade = "C";
        if (report.quality_score >= 9) grade = "A+";
        else if (report.quality_score >= 8) grade = "A";
        else if (report.quality_score >= 7) grade = "B";
        else if (report.quality_score >= 5) grade = "C";
        else grade = "F";
        
        gradeBadge.textContent = grade;
        
        const offset = 264 - (264 * report.quality_score * 10) / 100;
        gaugeProgress.style.strokeDashoffset = offset;
        
        if (report.quality_score >= 8) {
            gaugeProgress.style.stroke = "var(--accent-green)";
            gradeBadge.style.color = "var(--accent-green)";
            gradeBadge.style.borderColor = "var(--accent-green)";
            gradeDesc.textContent = "Excellent Code Health";
        } else if (report.quality_score >= 6) {
            gaugeProgress.style.stroke = "var(--accent-amber)";
            gradeBadge.style.color = "var(--accent-amber)";
            gradeBadge.style.borderColor = "var(--accent-amber)";
            gradeDesc.textContent = "Needs Refactoring";
        } else {
            gaugeProgress.style.stroke = "var(--accent-rose)";
            gradeBadge.style.color = "var(--accent-rose)";
            gradeBadge.style.borderColor = "var(--accent-rose)";
            gradeDesc.textContent = "High Risk Code Smells";
        }

        // Metrics Cards
        if (metricProjectName) metricProjectName.textContent = report.project_name;
        if (metricLastTime) {
            // format date
            const d = new Date(report.date);
            metricLastTime.textContent = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        }
        if (metricWarnings) metricWarnings.textContent = report.warnings;
        if (metricErrors) metricErrors.textContent = report.errors;
        if (metricSecurity) metricSecurity.textContent = report.security_issues;

        // Buttons
        if (report.pdf_report_path) {
            btnDownloadPdf.style.display = 'inline-flex';
            btnDownloadPdf.href = `/api/download_pdf/${report.report_id}`;
        } else {
            btnDownloadPdf.style.display = 'none';
        }
    }

    // Upload logic
    if (fileUploadInput) {
        fileUploadInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            pipelineStatus.textContent = "Status: Analyzing Uploaded File...";
            pipelineStatus.style.borderColor = "var(--accent-amber)";
            pipelineStatus.style.color = "var(--accent-amber)";
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/analyze_file', {
                    method: 'POST',
                    body: formData
                });
                if (!response.ok) throw new Error("Analysis failed");
                
                // Refresh history
                await fetchHistory();
            } catch (err) {
                console.error(err);
                pipelineStatus.textContent = "Status: Analysis Failed";
                pipelineStatus.style.borderColor = "var(--accent-rose)";
                pipelineStatus.style.color = "var(--accent-rose)";
            }
            // Reset input
            fileUploadInput.value = '';
        });
    }

    // Auto-fetch on load
    fetchHistory();
    // Poll every 10 seconds for new runs
    setInterval(fetchHistory, 10000);
});
