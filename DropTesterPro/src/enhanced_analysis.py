"""
Enhanced Analysis Module with ML Integration
Combines rule-based analysis with AI predictions and confidence scoring.
"""

import os
import json
import numpy as np
from typing import Dict, Tuple, Optional, List
from datetime import datetime

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

from . import analysis
from . import utils

class EnhancedAnalyzer:
    """Enhanced analyzer with ML integration and confidence scoring."""
    
    def __init__(self, model_path: str = None):
        """Initialize enhanced analyzer with optional ML model."""
        self.model = None
        self.model_available = False
        self.analysis_history = []
        
        # Load ML model if available
        if model_path and os.path.exists(model_path) and TF_AVAILABLE:
            try:
                self.model = tf.keras.models.load_model(model_path)
                self.model_available = True
                print(f"ML model loaded successfully from {model_path}")
            except Exception as e:
                print(f"Failed to load ML model: {e}")
        
        # Initialize confidence calibration parameters
        self.confidence_calibration = self._load_confidence_calibration()
    
    def _load_confidence_calibration(self) -> Dict:
        """Load confidence calibration parameters."""
        try:
            calibration_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "confidence_calibration.json"
            )
            
            if os.path.exists(calibration_file):
                with open(calibration_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load confidence calibration: {e}")
        
        # Default calibration parameters
        return {
            "rule_based_confidence": {
                "high_threshold": 0.85,
                "medium_threshold": 0.65,
                "deformation_scaling": 1.0,
                "spill_scaling": 0.9,
                "shatter_scaling": 0.8
            },
            "ml_confidence": {
                "certainty_threshold": 0.8,
                "uncertainty_penalty": 0.1
            },
            "hybrid_weights": {
                "rule_based": 0.6,
                "ml_based": 0.4
            }
        }
    
    def analyze_with_confidence(self, frame_before, frame_after, material_type: str = "Plastic",
                              use_ml: bool = True, save_for_training: bool = False) -> Dict:
        """
        Enhanced analysis with confidence scoring and optional ML integration.
        
        Args:
            frame_before: Frame before impact
            frame_after: Frame after impact
            material_type: Type of bottle material
            use_ml: Whether to use ML model if available
            save_for_training: Whether to save frames for training data
            
        Returns:
            Enhanced analysis result with confidence scores
        """
        timestamp = datetime.now().isoformat()
        
        # Perform rule-based analysis
        rule_result = analysis.analyze_bottle(frame_before, frame_after, material_type)
        
        # Calculate rule-based confidence
        rule_confidence = self._calculate_rule_confidence(rule_result, material_type)
        
        # Initialize result with rule-based analysis
        enhanced_result = {
            "timestamp": timestamp,
            "rule_based": rule_result,
            "rule_confidence": rule_confidence,
            "ml_prediction": None,
            "ml_confidence": 0.0,
            "final_result": rule_result["result"],
            "final_confidence": rule_confidence,
            "analysis_method": "rule_based",
            "agreement": True,
            "uncertainty_flags": []
        }
        
        # Add ML analysis if model is available and requested
        if self.model_available and use_ml and TF_AVAILABLE and CV2_AVAILABLE:
            try:
                ml_result = self._ml_predict(frame_before, frame_after)
                enhanced_result["ml_prediction"] = ml_result["prediction"]
                enhanced_result["ml_confidence"] = ml_result["confidence"]
                
                # Combine rule-based and ML results
                hybrid_result = self._combine_predictions(rule_result, ml_result, material_type)
                enhanced_result.update(hybrid_result)
                
            except Exception as e:
                enhanced_result["ml_error"] = str(e)
                enhanced_result["uncertainty_flags"].append("ml_error")
        
        # Add uncertainty analysis
        enhanced_result["uncertainty_analysis"] = self._analyze_uncertainty(enhanced_result)
        
        # Save for training if requested
        if save_for_training and CV2_AVAILABLE:
            self._save_training_sample(frame_before, frame_after, enhanced_result)
        
        # Store in analysis history
        self.analysis_history.append({
            "timestamp": timestamp,
            "result": enhanced_result["final_result"],
            "confidence": enhanced_result["final_confidence"],
            "method": enhanced_result["analysis_method"]
        })
        
        return enhanced_result
    
    def _calculate_rule_confidence(self, rule_result: Dict, material_type: str) -> float:
        """Calculate confidence score for rule-based analysis."""
        if rule_result.get("result") == "ERROR":
            return 0.0
        
        config = self.confidence_calibration["rule_based_confidence"]
        base_confidence = 0.5
        
        # Adjust confidence based on metric type and value
        metric = rule_result.get("metric", "")
        metric_value = rule_result.get("value", 0)
        
        if metric == "deformation":
            # Higher deformation values = higher confidence in FAIL
            # Lower deformation values = higher confidence in PASS
            if rule_result["result"] == "FAIL":
                base_confidence = min(0.95, 0.6 + (metric_value * config["deformation_scaling"]))
            else:
                base_confidence = min(0.95, 0.8 - (metric_value * config["deformation_scaling"]))
        
        elif metric == "spill_area":
            # Larger spill areas = higher confidence in FAIL
            normalized_spill = min(1.0, metric_value / 1000.0)  # Normalize to 0-1
            base_confidence = min(0.95, 0.7 + (normalized_spill * config["spill_scaling"]))
        
        elif metric == "shatter":
            # Shatter detection is generally high confidence
            base_confidence = config["shatter_scaling"]
        
        # Apply material-specific adjustments
        material_multiplier = {
            "Plastic": 1.0,
            "Steel": 0.9,  # Slightly less confident for steel
            "Glass": 1.1   # More confident for glass (clearer failure modes)
        }.get(material_type, 1.0)
        
        return min(0.99, base_confidence * material_multiplier)
    
    def _ml_predict(self, frame_before, frame_after) -> Dict:
        """Perform ML prediction on frame pair."""
        if not self.model_available or not CV2_AVAILABLE:
            raise RuntimeError("ML model or OpenCV not available")
        
        # Prepare input for the model (side-by-side frames)
        combined_frame = self._prepare_ml_input(frame_before, frame_after)
        
        # Make prediction
        prediction = self.model.predict(np.expand_dims(combined_frame, axis=0), verbose=0)
        
        # Assuming binary classification: [PASS_prob, FAIL_prob]
        pass_prob = float(prediction[0][0])
        fail_prob = float(prediction[0][1])
        
        # Determine prediction and confidence
        if pass_prob > fail_prob:
            result = "PASS"
            confidence = pass_prob
        else:
            result = "FAIL"
            confidence = fail_prob
        
        return {
            "prediction": result,
            "confidence": confidence,
            "pass_probability": pass_prob,
            "fail_probability": fail_prob
        }
    
    def _prepare_ml_input(self, frame_before, frame_after) -> np.ndarray:
        """Prepare input frames for ML model."""
        # Resize frames to expected model input size
        target_size = (128, 128)  # Assuming model expects 128x128 per frame
        
        frame_before_resized = cv2.resize(frame_before, target_size)
        frame_after_resized = cv2.resize(frame_after, target_size)
        
        # Combine frames side-by-side
        combined = np.hstack([frame_before_resized, frame_after_resized])
        
        # Normalize pixel values
        combined = combined.astype(np.float32) / 255.0
        
        return combined
    
    def _combine_predictions(self, rule_result: Dict, ml_result: Dict, material_type: str) -> Dict:
        """Combine rule-based and ML predictions using hybrid approach."""
        weights = self.confidence_calibration["hybrid_weights"]
        
        # Check for agreement
        agreement = rule_result["result"] == ml_result["prediction"]
        
        if agreement:
            # If both methods agree, use weighted confidence
            final_confidence = (
                rule_result.get("confidence", 0.5) * weights["rule_based"] +
                ml_result["confidence"] * weights["ml_based"]
            )
            final_result = rule_result["result"]
            method = "hybrid_agreement"
        else:
            # If methods disagree, use the one with higher confidence
            rule_conf = self._calculate_rule_confidence(rule_result, material_type)
            ml_conf = ml_result["confidence"]
            
            if rule_conf > ml_conf:
                final_result = rule_result["result"]
                final_confidence = rule_conf * 0.8  # Reduce confidence due to disagreement
                method = "rule_based_dominant"
            else:
                final_result = ml_result["prediction"]
                final_confidence = ml_conf * 0.8  # Reduce confidence due to disagreement
                method = "ml_dominant"
        
        return {
            "final_result": final_result,
            "final_confidence": min(0.99, final_confidence),
            "analysis_method": method,
            "agreement": agreement
        }
    
    def _analyze_uncertainty(self, result: Dict) -> Dict:
        """Analyze uncertainty factors in the prediction."""
        uncertainty_analysis = {
            "overall_uncertainty": 1.0 - result["final_confidence"],
            "confidence_level": self._get_confidence_level(result["final_confidence"]),
            "risk_factors": [],
            "recommendations": []
        }
        
        # Check for high uncertainty
        if result["final_confidence"] < 0.6:
            uncertainty_analysis["risk_factors"].append("Low overall confidence")
            uncertainty_analysis["recommendations"].append("Consider manual review")
        
        # Check for disagreement between methods
        if not result.get("agreement", True):
            uncertainty_analysis["risk_factors"].append("Method disagreement")
            uncertainty_analysis["recommendations"].append("Verify with additional testing")
        
        # Check for edge cases in rule-based analysis
        if result["rule_based"].get("metric_value", 0) > 0:
            metric_value = result["rule_based"]["metric_value"]
            if 0.1 < metric_value < 0.2:  # Border cases for deformation
                uncertainty_analysis["risk_factors"].append("Borderline deformation value")
                uncertainty_analysis["recommendations"].append("Consider retesting")
        
        return uncertainty_analysis
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Convert numerical confidence to categorical level."""
        if confidence >= 0.85:
            return "High"
        elif confidence >= 0.65:
            return "Medium"
        elif confidence >= 0.45:
            return "Low"
        else:
            return "Very Low"
    
    def _save_training_sample(self, frame_before, frame_after, result: Dict):
        """Save frames for training data collection."""
        try:
            # Create training directory structure
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "training_data"
            )
            
            result_dir = os.path.join(base_dir, result["final_result"])
            os.makedirs(result_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"sample_{timestamp}.jpg"
            
            # Combine frames side-by-side for training
            combined_frame = np.hstack([frame_before, frame_after])
            
            # Save the combined frame
            save_path = os.path.join(result_dir, filename)
            cv2.imwrite(save_path, combined_frame)
            
            # Save metadata
            metadata = {
                "timestamp": result["timestamp"],
                "result": result["final_result"],
                "confidence": result["final_confidence"],
                "method": result["analysis_method"],
                "rule_based_result": result["rule_based"],
                "ml_prediction": result.get("ml_prediction"),
                "uncertainty_analysis": result["uncertainty_analysis"]
            }
            
            metadata_path = os.path.join(result_dir, f"metadata_{timestamp}.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"Failed to save training sample: {e}")
    
    def get_model_performance_stats(self) -> Dict:
        """Get performance statistics for the ML model."""
        if not self.analysis_history:
            return {"error": "No analysis history available"}
        
        recent_analyses = self.analysis_history[-100:]  # Last 100 analyses
        
        method_counts = {}
        confidence_by_method = {}
        
        for analysis in recent_analyses:
            method = analysis["method"]
            confidence = analysis["confidence"]
            
            method_counts[method] = method_counts.get(method, 0) + 1
            
            if method not in confidence_by_method:
                confidence_by_method[method] = []
            confidence_by_method[method].append(confidence)
        
        # Calculate average confidence by method
        avg_confidence_by_method = {}
        for method, confidences in confidence_by_method.items():
            avg_confidence_by_method[method] = sum(confidences) / len(confidences)
        
        return {
            "total_analyses": len(recent_analyses),
            "method_distribution": method_counts,
            "average_confidence_by_method": avg_confidence_by_method,
            "model_available": self.model_available,
            "ml_integration_rate": (
                method_counts.get("hybrid_agreement", 0) + 
                method_counts.get("ml_dominant", 0)
            ) / len(recent_analyses) * 100 if recent_analyses else 0
        }
    
    def update_confidence_calibration(self, calibration_data: Dict):
        """Update confidence calibration parameters."""
        self.confidence_calibration.update(calibration_data)
        
        # Save updated calibration
        try:
            calibration_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "confidence_calibration.json"
            )
            
            with open(calibration_file, 'w') as f:
                json.dump(self.confidence_calibration, f, indent=2)
                
        except Exception as e:
            print(f"Failed to save confidence calibration: {e}")
    
    def auto_tune_thresholds(self, validation_data: List[Dict]) -> Dict:
        """Automatically tune analysis thresholds based on validation data."""
        if not validation_data:
            return {"error": "No validation data provided"}
        
        # This is a simplified threshold tuning - in practice, you'd use more sophisticated methods
        results = {
            "original_accuracy": 0,
            "tuned_accuracy": 0,
            "recommended_thresholds": {},
            "performance_improvement": 0
        }
        
        # Calculate original accuracy
        correct_predictions = 0
        for data in validation_data:
            predicted = data.get("predicted_result")
            actual = data.get("actual_result")
            if predicted == actual:
                correct_predictions += 1
        
        results["original_accuracy"] = correct_predictions / len(validation_data) * 100
        
        # For now, return the original accuracy
        # In a full implementation, you would:
        # 1. Try different threshold combinations
        # 2. Evaluate performance on validation set
        # 3. Select optimal thresholds
        # 4. Update configuration
        
        return results