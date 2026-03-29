# Tunisia Football AI - Coach Dashboard

A comprehensive, real-time AI-powered football analytics dashboard for coaches to track team performance, player metrics, fatigue levels, and match insights.

## Features

### 📊 Real-Time Match Statistics
- **Team Performance**: Live possession percentages, passes, and shots for both teams
- **Dynamic Updates**: Refresh data on-demand to see latest analysis results
- **Status Indicators**: Real-time data loading status

### 👥 Player Performance Tracking
- **Top 10 Players Table**: Sortable metrics including:
  - Total distance covered (meters)
  - Maximum speed (km/h)
  - Average speed (km/h)
  - Team assignments with color coding
- **Interactive Charts**:
  - Bar chart for distance distribution
  - Radar chart for speed comparison

### 💪 Fatigue Analysis
- **Overview Metrics**:
  - Average team fatigue percentage
  - Total tracked players
  - High-fatigue player count
- **Individual Player Cards**: Detailed breakdown showing:
  - Fatigue score (%)
  - Total distance covered
  - Sprint count
  - Color-coded alerts (red for high fatigue)

### ⚠️ AI Alerts & Insights
- **Smart Notifications**: AI-generated alerts for:
  - Injury risks
  - Fatigue warnings
  - Performance anomalies
  - Tactical recommendations
- **Severity Levels**: Color-coded by priority (high/medium/low)
- **Detailed Context**: Player ID, team, and actionable messages

### 🎥 Video Analysis Integration
- **Embedded Video Player**: Watch analyzed match footage directly in dashboard
- **Quick Links**:
  - Full HTML analysis reports
  - Advanced analytics PDFs
  - Heatmap visualizations

### 🎨 Modern UI/UX
- **Dark Theme**: Professional football-themed design optimized for long viewing sessions
- **Responsive Layout**: Works on desktop, tablet, and mobile devices
- **Smooth Animations**: Polished interactions and transitions
- **Accessible Navigation**: Sidebar menu with quick jump links

## Installation & Setup

### Prerequisites
- Python 3.6 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Quick Start

1. **Navigate to the Field_Fusion directory**:
   ```bash
   cd Field_Fusion
   ```

2. **Launch the dashboard**:
   ```bash
   python3 launch_dashboard.py
   ```

3. **Access the dashboard**:
   - The browser should open automatically
   - Or manually visit: `http://localhost:8080`

### Manual Setup (Alternative)

If you prefer to use your own web server:

```bash
# Using Python's built-in server
cd Field_Fusion
python3 -m http.server 8080

# Or using Node.js http-server
npx http-server -p 8080
```

Then open `http://localhost:8080/coach_dashboard.html` in your browser.

## Data Sources

The dashboard automatically loads data from these JSON files:

| Data Type | File Path | Description |
|-----------|-----------|-------------|
| Player Stats | `outputs/gradio_reports/player_stats.json` | Individual player metrics |
| Team Stats | `outputs/gradio_reports/team_stats.json` | Team-level possession and shots |
| Fatigue Data | `outputs/gradio_level3_reports/fatigue.json` | Player fatigue analysis |
| AI Alerts | `outputs/gradio_level3_reports/alerts.json` | Smart notifications and warnings |
| Video | `outputs/gradio_output.mp4` | Analyzed match footage |

## Dashboard Sections

### 1. Overview (Top Section)
- Real-time status indicator
- Quick-glance team comparison
- Fatigue summary

### 2. Player Performance
- Comprehensive table of top performers
- Team-based color coding
- Distance and speed metrics

### 3. Interactive Charts
- **Distance Distribution**: Bar chart showing player work rates
- **Speed Comparison**: Radar chart for max speed analysis

### 4. Fatigue Analysis
- Grid layout of player fatigue cards
- High-fatigue warnings highlighted in red
- Sprint and distance breakdowns

### 5. AI Alerts
- Priority-sorted alerts
- Severity-based color coding
- Actionable insights for coaches

### 6. Video Analysis
- Embedded video player with controls
- Links to detailed reports
- Access to heatmaps and advanced analytics

## Usage Tips

### Refreshing Data
- Click the "Refresh Data" button in the top navigation
- Data automatically loads on page refresh
- Status indicator shows loading state

### Interpreting Fatigue Scores
- **< 50%**: Normal fatigue levels (green)
- **50-70%**: Moderate fatigue (orange)
- **> 70%**: High fatigue - consider substitution (red)

### Navigation
- Use sidebar menu for quick section jumps
- All sections have anchor links (#players, #fatigue, #alerts, #video)
- Scroll smoothly through the entire dashboard

### Performance Optimization
- Dashboard loads data asynchronously
- Charts render after data is available
- Video is lazy-loaded for faster initial page load

## Customization

### Changing Colors
Edit the Tailwind config in `coach_dashboard.html` (lines 12-34):
```javascript
colors: {
    "primary": "#6dfe9c",  // Main team color
    "secondary": "#7799ff", // Opponent team color
    // ... more colors
}
```

### Adjusting Update Intervals
To auto-refresh data, add this to the script section:
```javascript
setInterval(loadData, 30000); // Refresh every 30 seconds
```

### Adding More Metrics
The dashboard can be extended to show:
- Pass networks (data available in `pass_networks.json`)
- Formation analysis (data in `formations.json`)
- Confidence scores (data in `confidence.json`)
- Match events (data in `events.json`)

## Troubleshooting

### Data Not Loading
1. Verify JSON files exist in `outputs/` directory
2. Check browser console (F12) for errors
3. Ensure file paths are correct
4. Confirm server is running in the correct directory

### Video Not Playing
- Check that `outputs/gradio_output.mp4` exists
- Try different video formats (.avi, .mp4)
- Verify video codec compatibility with your browser

### Charts Not Rendering
- Ensure Chart.js is loading (check browser console)
- Verify data format matches expected structure
- Clear browser cache and refresh

### Port Already in Use
If port 8080 is busy, edit `launch_dashboard.py`:
```python
PORT = 8081  # Change to any available port
```

## Technical Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Tailwind CSS v3
- **Charts**: Chart.js v4.4
- **Icons**: Google Material Symbols
- **Fonts**: Manrope, Inter
- **Server**: Python HTTP Server

## Data Flow

```
Video Analysis Pipeline
    ↓
JSON Data Files (outputs/)
    ↓
Dashboard JavaScript (fetch)
    ↓
DOM Updates & Chart Rendering
    ↓
Live Coach Dashboard
```

## Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Future Enhancements

Potential features for future versions:
- [ ] Real-time WebSocket updates during live matches
- [ ] Export reports as PDF
- [ ] Player comparison tool
- [ ] Historical match database
- [ ] Custom alert configuration
- [ ] Multi-language support
- [ ] Mobile app version
- [ ] Integration with wearable devices

## Support

For issues or questions:
1. Check the main project README
2. Review the COMPLETE_SYSTEM_SUMMARY.md
3. Examine browser console for errors
4. Verify all dependencies are installed

## License

Part of the Tunisia Football AI project - Field Fusion system.

---

**Made with ⚽ for football coaches using AI-powered analytics**
