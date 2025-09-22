"""
Analytics Dashboard UI for Bottle Drop Tester
Provides visual analytics and statistics interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import json
import os

from .analytics import TestAnalytics

class AnalyticsDashboard:
    """Analytics dashboard window for viewing test statistics and trends."""
    
    def __init__(self, parent_app, data_dir=None):
        """Initialize analytics dashboard."""
        self.parent_app = parent_app
        self.analytics = TestAnalytics(data_dir)
        self.window = None
        
    def show_dashboard(self):
        """Show the analytics dashboard window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        self.window = tk.Toplevel(self.parent_app.root)
        self.window.title("Test Analytics Dashboard")
        self.window.geometry("1200x800")
        self.window.minsize(1000, 600)
        
        # Configure grid
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Create tabs
        self._create_overview_tab()
        self._create_trends_tab()
        self._create_performance_tab()
        self._create_export_tab()
        
        # Load initial data
        self._refresh_all_data()
        
    def _create_overview_tab(self):
        """Create overview statistics tab."""
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="Overview")
        
        # Configure grid
        self.overview_frame.columnconfigure(0, weight=1)
        self.overview_frame.columnconfigure(1, weight=1)
        
        # Summary statistics frame
        summary_frame = ttk.LabelFrame(self.overview_frame, text="Summary Statistics (Last 30 Days)", padding=10)
        summary_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        summary_frame.columnconfigure(0, weight=1)
        
        # Summary statistics display
        self.summary_text = tk.Text(summary_frame, height=8, width=60, wrap=tk.WORD, state='disabled')
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        
        self.summary_text.grid(row=0, column=0, sticky="nsew")
        summary_scroll.grid(row=0, column=1, sticky="ns")
        
        # Material performance frame
        material_frame = ttk.LabelFrame(self.overview_frame, text="Performance by Material", padding=10)
        material_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        material_frame.columnconfigure(0, weight=1)
        material_frame.rowconfigure(1, weight=1)
        
        # Material treeview
        material_columns = ("Material", "Total Tests", "Pass Rate", "Avg Confidence")
        self.material_tree = ttk.Treeview(material_frame, columns=material_columns, show="headings", height=8)
        
        for col in material_columns:
            self.material_tree.heading(col, text=col)
            self.material_tree.column(col, width=120, anchor="center")
        
        material_scroll = ttk.Scrollbar(material_frame, orient="vertical", command=self.material_tree.yview)
        self.material_tree.configure(yscrollcommand=material_scroll.set)
        
        self.material_tree.grid(row=1, column=0, sticky="nsew")
        material_scroll.grid(row=1, column=1, sticky="ns")
        
        # Tester performance frame
        tester_frame = ttk.LabelFrame(self.overview_frame, text="Top Testers", padding=10)
        tester_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        tester_frame.columnconfigure(0, weight=1)
        tester_frame.rowconfigure(1, weight=1)
        
        # Tester treeview
        tester_columns = ("Tester", "Total Tests", "Pass Rate", "Override Rate")
        self.tester_tree = ttk.Treeview(tester_frame, columns=tester_columns, show="headings", height=8)
        
        for col in tester_columns:
            self.tester_tree.heading(col, text=col)
            self.tester_tree.column(col, width=120, anchor="center")
        
        tester_scroll = ttk.Scrollbar(tester_frame, orient="vertical", command=self.tester_tree.yview)
        self.tester_tree.configure(yscrollcommand=tester_scroll.set)
        
        self.tester_tree.grid(row=1, column=0, sticky="nsew")
        tester_scroll.grid(row=1, column=1, sticky="ns")
        
        # Refresh button
        refresh_btn = ttk.Button(self.overview_frame, text="Refresh Data", command=self._refresh_overview)
        refresh_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
    def _create_trends_tab(self):
        """Create trends analysis tab."""
        self.trends_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.trends_frame, text="Trends")
        
        # Configure grid
        self.trends_frame.columnconfigure(0, weight=1)
        self.trends_frame.rowconfigure(1, weight=1)
        
        # Controls frame
        controls_frame = ttk.Frame(self.trends_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ttk.Label(controls_frame, text="Time Period:").grid(row=0, column=0, padx=5)
        
        self.period_var = tk.StringVar(value="30")
        period_combo = ttk.Combobox(controls_frame, textvariable=self.period_var, 
                                   values=["7", "30", "90", "180", "365"], width=10, state="readonly")
        period_combo.grid(row=0, column=1, padx=5)
        period_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_trends())
        
        refresh_trends_btn = ttk.Button(controls_frame, text="Refresh Trends", command=self._refresh_trends)
        refresh_trends_btn.grid(row=0, column=2, padx=10)
        
        # Trends display frame
        trends_display_frame = ttk.LabelFrame(self.trends_frame, text="Daily Test Trends", padding=10)
        trends_display_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        trends_display_frame.columnconfigure(0, weight=1)
        trends_display_frame.rowconfigure(0, weight=1)
        
        # Trends treeview
        trends_columns = ("Date", "Total Tests", "Pass Count", "Fail Count", "Pass Rate %")
        self.trends_tree = ttk.Treeview(trends_display_frame, columns=trends_columns, show="headings")
        
        for col in trends_columns:
            self.trends_tree.heading(col, text=col)
            self.trends_tree.column(col, width=150, anchor="center")
        
        trends_scroll_v = ttk.Scrollbar(trends_display_frame, orient="vertical", command=self.trends_tree.yview)
        trends_scroll_h = ttk.Scrollbar(trends_display_frame, orient="horizontal", command=self.trends_tree.xview)
        self.trends_tree.configure(yscrollcommand=trends_scroll_v.set, xscrollcommand=trends_scroll_h.set)
        
        self.trends_tree.grid(row=0, column=0, sticky="nsew")
        trends_scroll_v.grid(row=0, column=1, sticky="ns")
        trends_scroll_h.grid(row=1, column=0, sticky="ew")
        
    def _create_performance_tab(self):
        """Create detailed performance analysis tab."""
        self.performance_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.performance_frame, text="Performance Analysis")
        
        # Configure grid
        self.performance_frame.columnconfigure(0, weight=1)
        self.performance_frame.rowconfigure(1, weight=1)
        
        # Analysis type selection
        analysis_frame = ttk.Frame(self.performance_frame)
        analysis_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ttk.Label(analysis_frame, text="Analysis Type:").grid(row=0, column=0, padx=5)
        
        self.analysis_type = tk.StringVar(value="failure_patterns")
        analysis_combo = ttk.Combobox(analysis_frame, textvariable=self.analysis_type,
                                     values=["failure_patterns", "material_analysis", "tester_analysis"],
                                     state="readonly", width=20)
        analysis_combo.grid(row=0, column=1, padx=5)
        analysis_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_performance())
        
        refresh_perf_btn = ttk.Button(analysis_frame, text="Refresh Analysis", command=self._refresh_performance)
        refresh_perf_btn.grid(row=0, column=2, padx=10)
        
        # Performance display
        self.performance_text = tk.Text(self.performance_frame, wrap=tk.WORD, state='disabled')
        performance_scroll = ttk.Scrollbar(self.performance_frame, orient="vertical", command=self.performance_text.yview)
        self.performance_text.configure(yscrollcommand=performance_scroll.set)
        
        self.performance_text.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        performance_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=5)
        
    def _create_export_tab(self):
        """Create data export tab."""
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="Data Export")
        
        # Export options frame
        export_options_frame = ttk.LabelFrame(self.export_frame, text="Export Options", padding=20)
        export_options_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        export_options_frame.columnconfigure(1, weight=1)
        
        # Format selection
        ttk.Label(export_options_frame, text="Export Format:").grid(row=0, column=0, sticky="w", pady=5)
        self.export_format = tk.StringVar(value="csv")
        format_frame = ttk.Frame(export_options_frame)
        format_frame.grid(row=0, column=1, sticky="w", pady=5)
        
        ttk.Radiobutton(format_frame, text="CSV", variable=self.export_format, value="csv").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="JSON", variable=self.export_format, value="json").pack(side=tk.LEFT, padx=10)
        
        # Date range selection
        ttk.Label(export_options_frame, text="Date Range:").grid(row=1, column=0, sticky="w", pady=5)
        date_frame = ttk.Frame(export_options_frame)
        date_frame.grid(row=1, column=1, sticky="w", pady=5)
        
        self.use_date_range = tk.BooleanVar(value=False)
        ttk.Checkbutton(date_frame, text="Use date range", variable=self.use_date_range).pack(side=tk.LEFT)
        
        ttk.Label(date_frame, text="From:").pack(side=tk.LEFT, padx=(20, 5))
        self.start_date = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        start_entry = ttk.Entry(date_frame, textvariable=self.start_date, width=12)
        start_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(date_frame, text="To:").pack(side=tk.LEFT, padx=(10, 5))
        self.end_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        end_entry = ttk.Entry(date_frame, textvariable=self.end_date, width=12)
        end_entry.pack(side=tk.LEFT, padx=5)
        
        # Export button
        export_btn = ttk.Button(export_options_frame, text="Export Data", command=self._export_data)
        export_btn.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Export status
        self.export_status = ttk.Label(export_options_frame, text="", foreground="green")
        self.export_status.grid(row=3, column=0, columnspan=2, pady=5)
        
    def _refresh_all_data(self):
        """Refresh all dashboard data."""
        self._refresh_overview()
        self._refresh_trends()
        self._refresh_performance()
        
    def _refresh_overview(self):
        """Refresh overview tab data."""
        try:
            # Update summary statistics
            stats = self.analytics.get_summary_stats(30)
            
            self.summary_text.config(state='normal')
            self.summary_text.delete(1.0, tk.END)
            
            summary_text = f"""
📊 SUMMARY STATISTICS (Last 30 Days)
═══════════════════════════════════════

🔢 Total Tests: {stats['total_tests']}
✅ Pass Count: {stats['pass_count']} ({stats['pass_rate']:.1f}%)
❌ Fail Count: {stats['fail_count']} ({stats['fail_rate']:.1f}%)
👥 Unique Testers: {stats['unique_testers']}
🧪 Material Types: {stats['material_types']}
🎯 Average Confidence: {stats['avg_confidence']:.2f}

📈 Key Insights:
• Pass Rate: {'High' if stats['pass_rate'] > 80 else 'Moderate' if stats['pass_rate'] > 60 else 'Low'} ({stats['pass_rate']:.1f}%)
• Test Volume: {'High' if stats['total_tests'] > 100 else 'Moderate' if stats['total_tests'] > 50 else 'Low'} ({stats['total_tests']} tests)
• Testing Consistency: {'Good' if stats['unique_testers'] > 1 else 'Single tester'}
            """.strip()
            
            self.summary_text.insert(1.0, summary_text)
            self.summary_text.config(state='disabled')
            
            # Update material performance
            self._update_material_tree()
            
            # Update tester performance
            self._update_tester_tree()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh overview data: {e}")
    
    def _update_material_tree(self):
        """Update material performance tree."""
        # Clear existing items
        for item in self.material_tree.get_children():
            self.material_tree.delete(item)
            
        try:
            material_stats = self.analytics.get_material_performance()
            
            for material, stats in material_stats.items():
                self.material_tree.insert("", "end", values=(
                    material,
                    stats['total_tests'],
                    f"{stats['pass_rate']:.1f}%",
                    f"{stats['avg_confidence']:.2f}"
                ))
                
        except Exception as e:
            print(f"Error updating material tree: {e}")
    
    def _update_tester_tree(self):
        """Update tester performance tree."""
        # Clear existing items
        for item in self.tester_tree.get_children():
            self.tester_tree.delete(item)
            
        try:
            tester_stats = self.analytics.get_tester_performance()
            
            # Sort by total tests and show top 10
            sorted_testers = sorted(tester_stats.items(), key=lambda x: x[1]['total_tests'], reverse=True)[:10]
            
            for tester, stats in sorted_testers:
                self.tester_tree.insert("", "end", values=(
                    tester,
                    stats['total_tests'],
                    f"{stats['pass_rate']:.1f}%",
                    f"{stats['override_rate']:.1f}%"
                ))
                
        except Exception as e:
            print(f"Error updating tester tree: {e}")
    
    def _refresh_trends(self):
        """Refresh trends tab data."""
        try:
            days = int(self.period_var.get())
            trend_data = self.analytics.get_trend_data(days)
            
            # Clear existing items
            for item in self.trends_tree.get_children():
                self.trends_tree.delete(item)
            
            # Add trend data
            for data in reversed(trend_data):  # Show most recent first
                self.trends_tree.insert("", "end", values=(
                    data['date'],
                    data['total_tests'],
                    data['pass_count'],
                    data['fail_count'],
                    f"{data['pass_rate']:.1f}%"
                ))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh trends data: {e}")
    
    def _refresh_performance(self):
        """Refresh performance analysis data."""
        try:
            analysis_type = self.analysis_type.get()
            
            self.performance_text.config(state='normal')
            self.performance_text.delete(1.0, tk.END)
            
            if analysis_type == "failure_patterns":
                patterns = self.analytics.get_failure_patterns()
                
                analysis_text = "🔍 FAILURE PATTERN ANALYSIS\n"
                analysis_text += "═" * 50 + "\n\n"
                
                if not patterns:
                    analysis_text += "No failure patterns found.\n"
                else:
                    for i, (reason, data) in enumerate(patterns.items(), 1):
                        analysis_text += f"{i}. {reason}\n"
                        analysis_text += f"   Total Occurrences: {data['total_frequency']}\n"
                        analysis_text += f"   By Material:\n"
                        for material, mat_data in data['by_material'].items():
                            analysis_text += f"     - {material}: {mat_data['frequency']} times\n"
                        analysis_text += "\n"
            
            elif analysis_type == "material_analysis":
                material_stats = self.analytics.get_material_performance()
                
                analysis_text = "🧪 MATERIAL ANALYSIS\n"
                analysis_text += "═" * 50 + "\n\n"
                
                for material, stats in material_stats.items():
                    analysis_text += f"📦 {material.upper()}\n"
                    analysis_text += f"   Total Tests: {stats['total_tests']}\n"
                    analysis_text += f"   Pass Rate: {stats['pass_rate']:.1f}%\n"
                    analysis_text += f"   Average Confidence: {stats['avg_confidence']:.2f}\n"
                    analysis_text += f"   Average Metric Value: {stats['avg_metric_value']:.2f}\n\n"
            
            elif analysis_type == "tester_analysis":
                tester_stats = self.analytics.get_tester_performance()
                
                analysis_text = "👥 TESTER ANALYSIS\n"
                analysis_text += "═" * 50 + "\n\n"
                
                sorted_testers = sorted(tester_stats.items(), key=lambda x: x[1]['total_tests'], reverse=True)
                
                for tester, stats in sorted_testers:
                    analysis_text += f"👤 {tester}\n"
                    analysis_text += f"   Total Tests: {stats['total_tests']}\n"
                    analysis_text += f"   Pass Rate: {stats['pass_rate']:.1f}%\n"
                    analysis_text += f"   Override Rate: {stats['override_rate']:.1f}%\n"
                    analysis_text += f"   Average Confidence: {stats['avg_confidence']:.2f}\n\n"
            
            self.performance_text.insert(1.0, analysis_text)
            self.performance_text.config(state='disabled')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh performance analysis: {e}")
    
    def _export_data(self):
        """Export data to file."""
        try:
            format_type = self.export_format.get()
            extension = "csv" if format_type == "csv" else "json"
            
            filename = filedialog.asksaveasfilename(
                title="Export Test Data",
                defaultextension=f".{extension}",
                filetypes=[(f"{format_type.upper()} files", f"*.{extension}"), ("All files", "*.*")]
            )
            
            if not filename:
                return
            
            start_date = self.start_date.get() if self.use_date_range.get() else None
            end_date = self.end_date.get() if self.use_date_range.get() else None
            
            success = self.analytics.export_data(filename, format_type, start_date, end_date)
            
            if success:
                self.export_status.config(text=f"✅ Data exported successfully to {os.path.basename(filename)}")
            else:
                self.export_status.config(text="❌ Export failed", foreground="red")
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {e}")
            self.export_status.config(text="❌ Export failed", foreground="red")