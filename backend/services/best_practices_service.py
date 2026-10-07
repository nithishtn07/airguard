"""
AirGuard AI - Environmental Best Practices Service
Phase 9: Practical guidance for:
A. Personal Exposure Reduction (sensitive groups, masks, ventilation, commute timing)
B. Community-Level Practices (transit, dust abatement, waste burning prevention)
C. Local Air-Quality Improvement (monitoring hotspots, anomaly tracking, emission compliance)

Conditioned dynamically on observed AQI and pollutant concentrations (e.g., elevated PM2.5).
Distinct from Phase 6 Dynamic Recommendations and Phase 9 Compliance Records.
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BestPracticesService:
    """
    Evaluates real air quality levels and returns structured, categorized best practices
    explicitly differentiated between Personal, Community, and Local Improvement domains.
    """

    def generate_best_practices(
        self,
        aqi: Optional[float] = None,
        pm25: Optional[float] = None,
        pm10: Optional[float] = None,
        dominant_pollutant: Optional[str] = None,
        location_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Produce categorized best practices conditioned on air quality condition.
        """
        if aqi is None and pm25 is None and pm10 is None:
            return {
                "condition_summary": "Environmental data unavailable",
                "condition_level": "unknown",
                "aqi_evaluated": None,
                "pm25_evaluated": None,
                "personal_exposure_reduction": [
                    {
                        "title": "Check Local Monitoring Regularly",
                        "description": "Condition-specific recommendations are unavailable because real-time air quality data could not be retrieved for this location.",
                        "priority": "low",
                        "category": "monitoring",
                    }
                ],
                "community_level_practices": [
                    {
                        "title": "Support Local Environmental Monitoring",
                        "description": "Advocate for low-cost sensor density or official CAAQMS station coverage in your municipality to bridge data gaps.",
                        "priority": "medium",
                        "category": "infrastructure",
                    }
                ],
                "local_air_quality_improvement": [
                    {
                        "title": "Report Local Pollution Sources",
                        "description": "Utilize official environmental authority grievance portals (e.g. CPCB Sameer app) to report unmonitored emission sources.",
                        "priority": "medium",
                        "category": "civic_action",
                    }
                ],
            }

        effective_aqi = aqi if aqi is not None else (pm25 * 2.0 if pm25 is not None else 50.0)
        is_pm25_elevated = pm25 is not None and pm25 > 60.0

        personal: List[Dict[str, Any]] = []
        community: List[Dict[str, Any]] = []
        local_improvement: List[Dict[str, Any]] = []

        if effective_aqi > 200 or (pm25 is not None and pm25 > 120.0):
            # Severe / Very Poor
            condition_level = "hazardous"
            condition_summary = f"Air quality is in the severe/hazardous range (AQI: {round(effective_aqi, 1)}). Immediate exposure mitigation required."

            personal = [
                {
                    "title": "Strict Outdoor Activity Curtailment",
                    "description": "Avoid strenuous outdoor exertion, morning jogging, and extended outdoor work during early morning and late evening inversion hours.",
                    "priority": "critical",
                    "category": "outdoor_activity",
                },
                {
                    "title": "Particulate Filtration (N95/FFP2)",
                    "description": "Wear certified well-fitted particulate respirators (N95, FFP2, or KF94) if outdoor transit is unavoidable. Surgical and cloth masks do not filter fine PM2.5.",
                    "priority": "critical",
                    "category": "protective_measures",
                },
                {
                    "title": "Seal Indoor Air & Run HEPA Cleaners",
                    "description": "Keep windows and exterior doors shut. Run indoor air purifiers equipped with true HEPA filters on continuous auto mode. Avoid indoor combustion (incense, smoking, frying).",
                    "priority": "high",
                    "category": "ventilation",
                },
                {
                    "title": "Vulnerable Populations Protection",
                    "description": "Children, the elderly, pregnant individuals, and those with cardiopulmonary or asthmatic conditions should strictly remain in filtered indoor environments.",
                    "priority": "critical",
                    "category": "sensitive_groups",
                },
            ]

            community = [
                {
                    "title": "Suspension of High-Dust Operations",
                    "description": "Enforce strict halt of dry earth excavation, unpaved vehicle movement, and non-essential demolition activities across urban wards.",
                    "priority": "critical",
                    "category": "dust_control",
                },
                {
                    "title": "Intensive Mechanized Water Sprinkling",
                    "description": "Deploy misting cannons and mechanized vacuum sweepers along primary transit corridors to prevent secondary particulate re-suspension.",
                    "priority": "high",
                    "category": "dust_control",
                },
                {
                    "title": "Strict Ban on Waste and Biomass Combustion",
                    "description": "Zero tolerance for leaf, garbage, or agricultural residue burning with active municipal neighborhood patrol surveillance.",
                    "priority": "critical",
                    "category": "waste_burning_prevention",
                },
                {
                    "title": "Transit Diversion and Public Fleet Prioritization",
                    "description": "Encourage carpooling, work-from-home contingencies, and frequency boost of electric metro/bus routes to suppress vehicular exhaust.",
                    "priority": "high",
                    "category": "transit",
                },
            ]

            local_improvement = [
                {
                    "title": "Immediate Verification of Industrial Stack Compliance",
                    "description": "Regulatory inspection of CEMS telemetry across surrounding industrial clusters to verify electrostatic precipitators and bag filters are functional.",
                    "priority": "critical",
                    "category": "industrial_compliance",
                },
                {
                    "title": "Targeted Hotspot Micro-Interventions",
                    "description": "Identify persistent micro-hotspots using local station telemetry and direct localized traffic redirection away from narrow residential canyons.",
                    "priority": "high",
                    "category": "hotspot_mitigation",
                },
                {
                    "title": "Civic Reporting via Environmental Grievance Apps",
                    "description": "Report visible chimney plume violations, generator emissions, or municipal fires via official authority reporting tools.",
                    "priority": "high",
                    "category": "public_reporting",
                },
            ]

        elif effective_aqi > 100 or is_pm25_elevated:
            # Moderate / Poor / Elevated PM2.5
            condition_level = "elevated"
            condition_summary = f"Elevated particulate and pollutant levels observed (AQI: {round(effective_aqi, 1)}). Precautionary practices recommended."

            personal = [
                {
                    "title": "Optimize Commuting and Outdoor Exercise Windows",
                    "description": "Shift outdoor exercise to mid-afternoon hours when planetary boundary layer mixing is highest and pollutant concentration is lowest. Avoid heavy traffic arteries.",
                    "priority": "high",
                    "category": "outdoor_activity",
                },
                {
                    "title": "Sensible Ventilation Management",
                    "description": "Ventilate indoor spaces briefly during afternoon hours when outdoor AQI is lowest. Keep windows closed during peak morning rush-hour smog.",
                    "priority": "medium",
                    "category": "ventilation",
                },
                {
                    "title": "Sensitive Individuals Precaution",
                    "description": "Persons with pre-existing respiratory or cardiovascular ailments should reduce prolonged exertion and keep relief medications readily accessible.",
                    "priority": "high",
                    "category": "sensitive_groups",
                },
                {
                    "title": "Cabin Air Recirculation in Transit",
                    "description": "Set vehicle HVAC to recirculate mode when driving through congested traffic corridors to minimize ingress of ultrafine tailpipe exhaust.",
                    "priority": "medium",
                    "category": "commuting",
                },
            ]

            community = [
                {
                    "title": "Dust Suppression at Active Worksites",
                    "description": "Ensure regular water sprinkling on unpaved building perimeters and mandate tarp covering for all haul trucks transporting aggregates.",
                    "priority": "high",
                    "category": "dust_control",
                },
                {
                    "title": "Shift to Mass Transit & Non-Motorized Mobility",
                    "description": "Encourage rail, bus, and cycling for short trips; reduce vehicle idling near school zones, hospital perimeters, and traffic intersections.",
                    "priority": "medium",
                    "category": "transit",
                },
                {
                    "title": "Composting over Organic Waste Burning",
                    "description": "Establish community composting bins for garden and leaf waste instead of burning dry foliage.",
                    "priority": "high",
                    "category": "waste_burning_prevention",
                },
            ]

            local_improvement = [
                {
                    "title": "Buffer Greenery and Vegetative Screens",
                    "description": "Promote multi-tier urban canopy planting (Ficus, Neem, Peepal) along arterial roads to act as biological particulate filtration barriers.",
                    "priority": "medium",
                    "category": "green_infrastructure",
                },
                {
                    "title": "Sensor Coverage Calibration and Hotspot Mapping",
                    "description": "Cross-reference hyper-local readings against regional CAAQMS stations to isolate persistent localized anomaly triggers.",
                    "priority": "medium",
                    "category": "monitoring_expansion",
                },
            ]

        else:
            # Good / Normal
            condition_level = "normal"
            condition_summary = f"Air quality is currently in the acceptable/normal range (AQI: {round(effective_aqi, 1)}). Maintain preventative clean-air habits."

            personal = [
                {
                    "title": "Optimal Outdoor Activity & Natural Ventilation",
                    "description": "Conditions are favorable for outdoor recreation, sports, and natural whole-house ventilation to refresh indoor air quality.",
                    "priority": "low",
                    "category": "outdoor_activity",
                },
                {
                    "title": "Maintain Active Clean Travel Habits",
                    "description": "Continue walking, cycling, or utilizing public transportation to keep urban emissions low and sustain healthy air quality.",
                    "priority": "low",
                    "category": "commuting",
                },
            ]

            community = [
                {
                    "title": "Sustained Low-Emission Mobility Promotion",
                    "description": "Maintain regular vehicle emission certification (PUC) checks and support transition to electric mobility.",
                    "priority": "low",
                    "category": "transit",
                },
                {
                    "title": "Urban Greening and Tree Canopy Protection",
                    "description": "Support urban forestry and native flora preservation across residential parks and school zones.",
                    "priority": "low",
                    "category": "green_infrastructure",
                },
            ]

            local_improvement = [
                {
                    "title": "Continuous Baseline Telemetry Monitoring",
                    "description": "Maintain continuous air quality monitoring to detect early warning spikes or seasonal meteorological inversions.",
                    "priority": "low",
                    "category": "monitoring",
                },
                {
                    "title": "Proactive Urban Emission Audits",
                    "description": "Ensure ongoing compliance with clean air action plans before winter or adverse meteorological conditions set in.",
                    "priority": "low",
                    "category": "policy",
                },
            ]

        return {
            "condition_summary": condition_summary,
            "condition_level": condition_level,
            "aqi_evaluated": round(effective_aqi, 1),
            "pm25_evaluated": round(pm25, 1) if pm25 is not None else None,
            "location_context": location_name or "Selected Region",
            "personal_exposure_reduction": personal,
            "community_level_practices": community,
            "local_air_quality_improvement": local_improvement,
        }


# Singleton instance
best_practices_service = BestPracticesService()
