#!/usr/bin/env python3
"""
Generate Human-Readable PDF Reports from JSON Data
Creates beautiful, professional reports that coaches can easily read and understand
"""

import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas

def load_json(filepath):
    """Load JSON data from file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def create_header_style():
    """Create custom styles for the report"""
    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#19be64'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#6dfe9c'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    # Body style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        fontName='Helvetica'
    )

    return title_style, heading_style, body_style

def generate_match_summary_pdf(output_dir):
    """Generate a comprehensive match summary PDF"""
    print("📄 Generating Match Summary Report...")

    # Load data
    player_stats = load_json(output_dir / 'gradio_reports' / 'player_stats.json')
    team_stats = load_json(output_dir / 'gradio_reports' / 'team_stats.json')
    events = load_json(output_dir / 'gradio_reports' / 'events.json')
    formations = load_json(output_dir / 'gradio_level3_reports' / 'formations.json')

    if not all([player_stats, team_stats]):
        print("❌ Missing required data files")
        return

    # Create PDF
    pdf_path = output_dir / 'MATCH_SUMMARY_REPORT.pdf'
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)

    story = []
    title_style, heading_style, body_style = create_header_style()

    # Title
    story.append(Paragraph("⚽ MATCH ANALYSIS REPORT", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    story.append(Spacer(1, 0.3*inch))

    # Team Statistics
    story.append(Paragraph("📊 TEAM STATISTICS", heading_style))

    team_data = [
        ['Metric', 'Team 1', 'Team 2'],
        ['Possession %',
         f"{team_stats['team_1']['possession_percent']:.1f}%",
         f"{team_stats['team_2']['possession_percent']:.1f}%"],
        ['Total Passes',
         str(team_stats['team_1']['total_passes']),
         str(team_stats['team_2']['total_passes'])],
        ['Total Shots',
         str(team_stats['team_1']['total_shots']),
         str(team_stats['team_2']['total_shots'])],
    ]

    team_table = Table(team_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    team_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#19be64')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))

    story.append(team_table)
    story.append(Spacer(1, 0.3*inch))

    # Top Players
    story.append(Paragraph("🏆 TOP 10 PLAYER PERFORMANCES", heading_style))

    player_data = [['Rank', 'Player ID', 'Team', 'Distance (m)', 'Max Speed (km/h)', 'Avg Speed (km/h)']]

    for i, player in enumerate(player_stats[:10], 1):
        player_data.append([
            str(i),
            str(player['player_id']),
            f"Team {player['team']}",
            f"{player['total_distance_m']:.1f}",
            f"{player['max_speed_kmh']:.1f}",
            f"{player['avg_speed_kmh']:.1f}"
        ])

    player_table = Table(player_data, colWidths=[0.6*inch, 1*inch, 0.8*inch, 1.2*inch, 1.4*inch, 1.4*inch])
    player_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6dfe9c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))

    story.append(player_table)
    story.append(Spacer(1, 0.3*inch))

    # Match Events
    if events:
        story.append(Paragraph("⚡ MATCH EVENTS SUMMARY", heading_style))

        summary_text = f"""
        <b>Total Passes:</b> {events.get('summary', {}).get('total_passes', 'N/A')}<br/>
        <b>Total Shots:</b> {events.get('summary', {}).get('total_shots', 'N/A')}<br/>
        <b>Total Interceptions:</b> {events.get('summary', {}).get('total_interceptions', 'N/A')}<br/>
        """
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 0.2*inch))

        # Key Events
        if events.get('shots'):
            story.append(Paragraph("🎯 Shots on Goal:", body_style))
            for shot in events['shots']:
                shot_text = f"• Frame {shot['frame']}: Player {shot['player']} (Team {shot['team']}) - Speed: {shot['speed']:.1f} km/h"
                story.append(Paragraph(shot_text, body_style))

    # Formations
    if formations and formations.get('formations'):
        story.append(PageBreak())
        story.append(Paragraph("🎯 TACTICAL FORMATIONS", heading_style))

        for team_id, formation in formations['formations'].items():
            team_text = f"""
            <b>Team {team_id}:</b> {formation['formation_name']}<br/>
            <b>Tactical State:</b> {formation['tactical_state'].title()}<br/>
            <b>Compactness:</b> {formation['shape']['compactness']:.2f}<br/>
            <b>Width:</b> {formation['shape']['width']:.1f}m<br/>
            <b>Depth:</b> {formation['shape']['depth']:.1f}m<br/>
            """
            story.append(Paragraph(team_text, body_style))
            story.append(Spacer(1, 0.2*inch))

    # Build PDF
    doc.build(story)
    print(f"✅ Match Summary Report saved: {pdf_path}")
    return pdf_path

def generate_fatigue_report_pdf(output_dir):
    """Generate a human-readable fatigue analysis PDF"""
    print("📄 Generating Fatigue Analysis Report...")

    fatigue_data = load_json(output_dir / 'gradio_level3_reports' / 'fatigue.json')

    if not fatigue_data:
        print("❌ Missing fatigue data")
        return

    pdf_path = output_dir / 'FATIGUE_ANALYSIS_REPORT.pdf'
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)

    story = []
    title_style, heading_style, body_style = create_header_style()

    # Title
    story.append(Paragraph("💪 PLAYER FATIGUE ANALYSIS", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    story.append(Spacer(1, 0.3*inch))

    # Summary
    story.append(Paragraph("📊 FATIGUE OVERVIEW", heading_style))

    summary_data = [
        ['Metric', 'Value'],
        ['Total Players Tracked', str(fatigue_data.get('total_players', 'N/A'))],
        ['Average Fatigue Score', f"{fatigue_data.get('average_fatigue', 0) * 100:.1f}%"],
        ['High Fatigue Players', str(fatigue_data.get('high_fatigue_count', 0))],
    ]

    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#19be64')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))

    # Top Fatigued Players
    if fatigue_data.get('players'):
        story.append(Paragraph("⚠️ HIGH FATIGUE PLAYERS (Requires Attention)", heading_style))

        # Sort by fatigue score
        players_list = []
        for player_id, player in fatigue_data['players'].items():
            players_list.append({
                'id': player_id,
                'fatigue': player['scores']['fatigue_score'],
                'data': player
            })

        players_list.sort(key=lambda x: x['fatigue'], reverse=True)

        fatigue_data_table = [['Player ID', 'Team', 'Fatigue %', 'Distance (m)', 'Sprints', 'Status']]

        for p in players_list[:15]:  # Top 15
            fatigue_percent = p['fatigue'] * 100
            status = '🔴 HIGH' if fatigue_percent > 70 else '🟡 MEDIUM' if fatigue_percent > 50 else '🟢 NORMAL'

            fatigue_data_table.append([
                str(p['id']),
                f"Team {p['data']['team']}",
                f"{fatigue_percent:.1f}%",
                f"{p['data']['distances']['total']:.1f}",
                str(p['data']['intensity_metrics']['sprint_count']),
                status
            ])

        player_fatigue_table = Table(fatigue_data_table,
                                     colWidths=[0.8*inch, 0.8*inch, 1*inch, 1.2*inch, 0.8*inch, 1.2*inch])
        player_fatigue_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff716c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))

        story.append(player_fatigue_table)
        story.append(Spacer(1, 0.3*inch))

        # Recommendations
        story.append(Paragraph("💡 COACHING RECOMMENDATIONS", heading_style))

        high_fatigue = [p for p in players_list if p['fatigue'] > 0.7]

        if high_fatigue:
            recs = f"""
            <b>⚠️ IMMEDIATE ATTENTION REQUIRED:</b><br/>
            • {len(high_fatigue)} player(s) showing high fatigue levels (>70%)<br/>
            • Consider substitutions for: {', '.join([f"Player {p['id']}" for p in high_fatigue[:5]])}<br/>
            • Recommend rest period: 48-72 hours<br/>
            • Monitor for injury risk in next training session<br/>
            """
        else:
            recs = """
            <b>✅ TEAM STATUS: GOOD</b><br/>
            • No players showing critical fatigue levels<br/>
            • Continue normal training schedule<br/>
            • Maintain monitoring during next match<br/>
            """

        story.append(Paragraph(recs, body_style))

    # Build PDF
    doc.build(story)
    print(f"✅ Fatigue Analysis Report saved: {pdf_path}")
    return pdf_path

def generate_tactical_report_pdf(output_dir):
    """Generate tactical analysis PDF"""
    print("📄 Generating Tactical Analysis Report...")

    formations = load_json(output_dir / 'gradio_level3_reports' / 'formations.json')
    pass_networks = load_json(output_dir / 'gradio_level3_reports' / 'pass_networks.json')
    pressing = load_json(output_dir / 'gradio_level3_reports' / 'pressing.json')

    if not all([formations, pass_networks, pressing]):
        print("❌ Missing tactical data files")
        return

    pdf_path = output_dir / 'TACTICAL_ANALYSIS_REPORT.pdf'
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)

    story = []
    title_style, heading_style, body_style = create_header_style()

    # Title
    story.append(Paragraph("🎯 TACTICAL ANALYSIS REPORT", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    story.append(Spacer(1, 0.3*inch))

    # Formations
    story.append(Paragraph("⚙️ TEAM FORMATIONS", heading_style))

    if formations.get('formations'):
        form_data = [['Team', 'Formation', 'State', 'Compactness', 'Width (m)', 'Depth (m)']]

        for team_id, form in formations['formations'].items():
            form_data.append([
                f"Team {team_id}",
                form['formation_name'],
                form['tactical_state'].title(),
                f"{form['shape']['compactness']:.2f}",
                f"{form['shape']['width']:.1f}",
                f"{form['shape']['depth']:.1f}"
            ])

        form_table = Table(form_data, colWidths=[0.8*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch, 1*inch])
        form_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6dfe9c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ]))

        story.append(form_table)
        story.append(Spacer(1, 0.3*inch))

    # Pass Networks
    story.append(Paragraph("🔗 PASSING ANALYSIS", heading_style))

    if pass_networks.get('pass_networks'):
        pass_data = [['Team', 'Total Passes', 'Completed', 'Accuracy %', 'Network Density']]

        for team_id, pn in pass_networks['pass_networks'].items():
            pass_data.append([
                f"Team {team_id}",
                str(pn['passes']['total']),
                str(pn['passes']['completed']),
                f"{pn['passes']['accuracy_percent']:.1f}%",
                f"{pn['network_structure']['network_density']:.2f}"
            ])

        pass_table = Table(pass_data, colWidths=[1*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.5*inch])
        pass_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7799ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ]))

        story.append(pass_table)
        story.append(Spacer(1, 0.3*inch))

    # Pressing Metrics
    story.append(Paragraph("🛡️ DEFENSIVE PRESSING", heading_style))

    if pressing.get('pressing_metrics'):
        press_data = [['Team', 'Intensity', 'High Press %', 'PPDA', 'Recovery (s)', 'Def Line']]

        for team_id, pm in pressing['pressing_metrics'].items():
            press_data.append([
                f"Team {team_id}",
                f"{pm['pressing']['intensity']:.2f}",
                f"{pm['pressing']['high_press_percentage']:.1f}%",
                f"{pm['defensive_actions']['ppda']:.2f}",
                f"{pm['defensive_actions']['recovery_speed_seconds']:.1f}",
                f"{pm['pressing']['defensive_line_height']:.0f}"
            ])

        press_table = Table(press_data, colWidths=[0.8*inch, 1*inch, 1.2*inch, 0.8*inch, 1.2*inch, 1*inch])
        press_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ffb148')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ]))

        story.append(press_table)

    # Build PDF
    doc.build(story)
    print(f"✅ Tactical Analysis Report saved: {pdf_path}")
    return pdf_path

def main():
    """Generate all readable PDF reports"""
    print("\n" + "="*60)
    print("🎯 GENERATING HUMAN-READABLE PDF REPORTS")
    print("="*60 + "\n")

    output_dir = Path(__file__).parent / 'outputs'

    if not output_dir.exists():
        print(f"❌ Output directory not found: {output_dir}")
        return

    # Generate reports
    reports_generated = []

    try:
        report = generate_match_summary_pdf(output_dir)
        if report:
            reports_generated.append(report)
    except Exception as e:
        print(f"❌ Error generating match summary: {e}")

    try:
        report = generate_fatigue_report_pdf(output_dir)
        if report:
            reports_generated.append(report)
    except Exception as e:
        print(f"❌ Error generating fatigue report: {e}")

    try:
        report = generate_tactical_report_pdf(output_dir)
        if report:
            reports_generated.append(report)
    except Exception as e:
        print(f"❌ Error generating tactical report: {e}")

    # Summary
    print("\n" + "="*60)
    print(f"✅ COMPLETE: {len(reports_generated)} PDF reports generated")
    print("="*60)

    for report in reports_generated:
        print(f"  📄 {report.name}")

    print("\n💡 These PDFs are fully formatted and human-readable!")
    print("   Open them with any PDF reader to view.\n")

if __name__ == "__main__":
    main()
