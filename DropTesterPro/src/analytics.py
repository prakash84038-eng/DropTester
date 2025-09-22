"""
Statistical Analytics Module for Bottle Drop Tester
Provides analytics and trend analysis for test results.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import csv

class TestAnalytics:
    """Handles collection and analysis of test statistics."""
    
    def __init__(self, data_dir: str = None):
        """Initialize analytics with data directory."""
        if data_dir is None:
            data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "test_analytics.db")
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for storing test analytics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sample_code TEXT,
                is_number TEXT,
                parameter TEXT,
                department TEXT,
                testing_person TEXT,
                material_type TEXT,
                result TEXT NOT NULL,
                confidence REAL,
                metric TEXT,
                metric_value REAL,
                reason TEXT,
                video_path TEXT,
                pdf_path TEXT,
                manual_override BOOLEAN DEFAULT 0
            )
        """)
        
        # Create analytics_summary table for cached statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_tests INTEGER,
                pass_count INTEGER,
                fail_count INTEGER,
                material_breakdown TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_test_result(self, test_data: Dict) -> int:
        """Record a test result in the analytics database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tests (
                timestamp, sample_code, is_number, parameter, department,
                testing_person, material_type, result, confidence, metric,
                metric_value, reason, video_path, pdf_path, manual_override
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_data.get('timestamp', datetime.now().isoformat()),
            test_data.get('sample_code', ''),
            test_data.get('is_number', ''),
            test_data.get('parameter', ''),
            test_data.get('department', ''),
            test_data.get('testing_person', ''),
            test_data.get('material_type', ''),
            test_data.get('result', ''),
            test_data.get('confidence', None),
            test_data.get('metric', ''),
            test_data.get('metric_value', None),
            test_data.get('reason', ''),
            test_data.get('video_path', ''),
            test_data.get('pdf_path', ''),
            test_data.get('manual_override', False)
        ))
        
        test_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Update summary statistics
        self._update_daily_summary()
        
        return test_id
    
    def _update_daily_summary(self):
        """Update daily summary statistics."""
        today = datetime.now().date().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get today's statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as fail_count,
                material_type
            FROM tests 
            WHERE DATE(timestamp) = ?
            GROUP BY material_type
        """, (today,))
        
        results = cursor.fetchall()
        
        if results:
            total_tests = sum(r[0] for r in results)
            total_pass = sum(r[1] for r in results)
            total_fail = sum(r[2] for r in results)
            
            material_breakdown = {r[3]: {'total': r[0], 'pass': r[1], 'fail': r[2]} 
                                for r in results if r[3]}
            
            # Update or insert summary
            cursor.execute("""
                INSERT OR REPLACE INTO analytics_summary 
                (date, total_tests, pass_count, fail_count, material_breakdown, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                today, total_tests, total_pass, total_fail,
                json.dumps(material_breakdown), datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def get_summary_stats(self, days: int = 30) -> Dict:
        """Get summary statistics for the last N days."""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_tests,
                SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as fail_count,
                COUNT(DISTINCT testing_person) as unique_testers,
                COUNT(DISTINCT material_type) as material_types,
                AVG(CASE WHEN confidence IS NOT NULL THEN confidence END) as avg_confidence
            FROM tests 
            WHERE DATE(timestamp) BETWEEN ? AND ?
        """, (start_date.isoformat(), end_date.isoformat()))
        
        result = cursor.fetchone()
        conn.close()
        
        total_tests = result[0] or 0
        pass_count = result[1] or 0
        fail_count = result[2] or 0
        
        return {
            'period_days': days,
            'total_tests': total_tests,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'pass_rate': (pass_count / total_tests * 100) if total_tests > 0 else 0,
            'fail_rate': (fail_count / total_tests * 100) if total_tests > 0 else 0,
            'unique_testers': result[3] or 0,
            'material_types': result[4] or 0,
            'avg_confidence': result[5] or 0
        }
    
    def get_trend_data(self, days: int = 30) -> List[Dict]:
        """Get daily trend data for charts."""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                DATE(timestamp) as test_date,
                COUNT(*) as total_tests,
                SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
            FROM tests 
            WHERE DATE(timestamp) BETWEEN ? AND ?
            GROUP BY DATE(timestamp)
            ORDER BY test_date
        """, (start_date.isoformat(), end_date.isoformat()))
        
        results = cursor.fetchall()
        conn.close()
        
        trend_data = []
        for row in results:
            date, total, pass_count, fail_count = row
            trend_data.append({
                'date': date,
                'total_tests': total,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'pass_rate': (pass_count / total * 100) if total > 0 else 0
            })
        
        return trend_data
    
    def get_material_performance(self) -> Dict[str, Dict]:
        """Get performance statistics by material type."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                material_type,
                COUNT(*) as total_tests,
                SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as fail_count,
                AVG(CASE WHEN confidence IS NOT NULL THEN confidence END) as avg_confidence,
                AVG(CASE WHEN metric_value IS NOT NULL THEN metric_value END) as avg_metric
            FROM tests 
            WHERE material_type IS NOT NULL AND material_type != ''
            GROUP BY material_type
        """, )
        
        results = cursor.fetchall()
        conn.close()
        
        material_stats = {}
        for row in results:
            material, total, pass_count, fail_count, avg_conf, avg_metric = row
            material_stats[material] = {
                'total_tests': total,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'pass_rate': (pass_count / total * 100) if total > 0 else 0,
                'avg_confidence': avg_conf or 0,
                'avg_metric_value': avg_metric or 0
            }
        
        return material_stats
    
    def get_tester_performance(self) -> Dict[str, Dict]:
        """Get performance statistics by testing person."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                testing_person,
                COUNT(*) as total_tests,
                SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as fail_count,
                SUM(CASE WHEN manual_override = 1 THEN 1 ELSE 0 END) as override_count,
                AVG(CASE WHEN confidence IS NOT NULL THEN confidence END) as avg_confidence
            FROM tests 
            WHERE testing_person IS NOT NULL AND testing_person != ''
            GROUP BY testing_person
            ORDER BY total_tests DESC
        """, )
        
        results = cursor.fetchall()
        conn.close()
        
        tester_stats = {}
        for row in results:
            tester, total, pass_count, fail_count, override_count, avg_conf = row
            tester_stats[tester] = {
                'total_tests': total,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'pass_rate': (pass_count / total * 100) if total > 0 else 0,
                'override_rate': (override_count / total * 100) if total > 0 else 0,
                'avg_confidence': avg_conf or 0
            }
        
        return tester_stats
    
    def export_data(self, output_path: str, format: str = 'csv', 
                   start_date: str = None, end_date: str = None) -> bool:
        """Export test data to CSV or JSON format."""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = "SELECT * FROM tests"
            params = []
            
            if start_date or end_date:
                query += " WHERE"
                if start_date:
                    query += " DATE(timestamp) >= ?"
                    params.append(start_date)
                if end_date:
                    if start_date:
                        query += " AND"
                    query += " DATE(timestamp) <= ?"
                    params.append(end_date)
            
            query += " ORDER BY timestamp DESC"
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            columns = [description[0] for description in cursor.description]
            data = cursor.fetchall()
            
            if format.lower() == 'csv':
                with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(columns)
                    writer.writerows(data)
            
            elif format.lower() == 'json':
                json_data = []
                for row in data:
                    json_data.append(dict(zip(columns, row)))
                
                with open(output_path, 'w', encoding='utf-8') as jsonfile:
                    json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error exporting data: {e}")
            return False
    
    def get_failure_patterns(self) -> Dict:
        """Analyze failure patterns and common reasons."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                reason,
                COUNT(*) as frequency,
                material_type,
                AVG(metric_value) as avg_metric
            FROM tests 
            WHERE result = 'FAIL' AND reason IS NOT NULL
            GROUP BY reason, material_type
            ORDER BY frequency DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        patterns = {}
        for row in results:
            reason, freq, material, avg_metric = row
            if reason not in patterns:
                patterns[reason] = {
                    'total_frequency': 0,
                    'by_material': {},
                    'avg_metric_value': 0
                }
            
            patterns[reason]['total_frequency'] += freq
            patterns[reason]['by_material'][material or 'Unknown'] = {
                'frequency': freq,
                'avg_metric': avg_metric or 0
            }
        
        return patterns
    
    def cleanup_old_data(self, days_to_keep: int = 365):
        """Remove old test data beyond retention period."""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).date()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM tests WHERE DATE(timestamp) < ?", (cutoff_date.isoformat(),))
        cursor.execute("DELETE FROM analytics_summary WHERE date < ?", (cutoff_date.isoformat(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count