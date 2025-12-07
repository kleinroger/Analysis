from flask import render_template, request, jsonify
from flask_login import login_required
from app.models import AnalysisReport
from app import db
from . import bp

@bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')

@bp.route('/api/list')
@login_required
def list_reports():
    keyword = request.args.get('keyword', '')
    
    query = AnalysisReport.query
    if keyword:
        query = query.filter(AnalysisReport.title.contains(keyword))
        
    reports = query.order_by(AnalysisReport.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reports])

@bp.route('/api/save', methods=['POST'])
@login_required
def save_report():
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    report_type = data.get('report_type', 'general')
    
    if not title or not content:
        return jsonify({'success': False, 'error': '标题和内容不能为空'})
        
    report = AnalysisReport(title=title, content=content, report_type=report_type)
    db.session.add(report)
    db.session.commit()
    return jsonify({'success': True, 'id': report.id})

@bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_report(id):
    report = AnalysisReport.query.get_or_404(id)
    db.session.delete(report)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/detail/<int:id>')
@login_required
def get_report(id):
    report = AnalysisReport.query.get_or_404(id)
    return jsonify(report.to_dict())
