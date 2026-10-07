#!/usr/bin/env python3
"""
Predictive Sales Forecasting & Monte Carlo Simulation Engine
Fournit des projections statistiques avancées sur l'atteinte des objectifs du Directeur :
- Simulation Monte Carlo sur 1 000 itérations basées sur la vélocité des ventes
- Calcul des trajectoires Pessimiste (10e percentile), Réaliste (médiane) et Optimiste (90e percentile)
- Analyse d'écart (Gap Analysis) et recommandations chiffrées
Auteur : Agent IA Commercial
"""

import math
import random
from typing import Dict, Any, List
from datetime import date, datetime

class SalesForecastingEngine:
    def __init__(self):
        pass

    def run_monte_carlo_simulation(
        self,
        current_revenue: float,
        target_revenue: float,
        days_remaining: int = 15,
        avg_deal_size: float = 15000,
        historical_daily_deals_mean: float = 1.2,
        historical_daily_deals_std: float = 0.5,
        iterations: int = 1000
    ) -> Dict[str, Any]:
        """
        Exécute 1 000 simulations stochastiques pour déterminer la probabilité d'atteinte du CA
        """
        random.seed(42)  # Pour la reproductibilité
        simulation_results = []
        target_achieved_count = 0

        # Trajectoires journalières cumulées
        daily_trajectories = [[] for _ in range(days_remaining + 1)]

        for _ in range(iterations):
            rev = current_revenue
            daily_trajectories[0].append(rev)

            for d in range(1, days_remaining + 1):
                # Nombre de ventes ce jour selon une distribution normale tronquée
                deals_today = max(0, random.gauss(historical_daily_deals_mean, historical_daily_deals_std))
                # Variation du panier moyen (+/- 20%)
                deal_value_variation = avg_deal_size * (1 + random.uniform(-0.2, 0.25))
                rev += deals_today * deal_value_variation
                daily_trajectories[d].append(rev)

            simulation_results.append(rev)
            if rev >= target_revenue:
                target_achieved_count += 1

        simulation_results.sort()

        # Calcul des percentiles
        p10_idx = int(0.10 * iterations)
        p50_idx = int(0.50 * iterations)
        p90_idx = int(0.90 * iterations)

        pessimistic_rev = round(simulation_results[p10_idx], 0)
        realistic_rev = round(simulation_results[p50_idx], 0)
        optimistic_rev = round(simulation_results[p90_idx], 0)

        probability_pct = round((target_achieved_count / iterations) * 100, 1)

        # Calcul des trajectoires médianes et percentiles par jour
        trajectories_chart = []
        for d in range(days_remaining + 1):
            day_data = sorted(daily_trajectories[d])
            trajectories_chart.append({
                "jour": f"J+{d}",
                "pessimiste": round(day_data[int(0.10 * iterations)]),
                "realiste": round(day_data[int(0.50 * iterations)]),
                "optimiste": round(day_data[int(0.90 * iterations)])
            })

        # Gap Analysis
        gap_amount = max(0, target_revenue - realistic_rev)
        missing_deals = math.ceil(gap_amount / avg_deal_size) if gap_amount > 0 else 0

        advice = ""
        if probability_pct >= 85:
            advice = "🟢 Trajectoire ultra-sécurisée. L'objectif sera dépassé selon les projections statistiques."
        elif probability_pct >= 60:
            advice = f"🟡 Objectif atteignable avec une saine intensité. {missing_deals} ventes additionnelles requises pour atteindre 100% de certitude."
        else:
            advice = f"🔴 Alerte décalage : Intensifier le volume d'appels à froid et les relances à 48h. Il manque environ {missing_deals} ventes."

        return {
            "target_revenue": target_revenue,
            "current_revenue": current_revenue,
            "probability_pct": probability_pct,
            "days_remaining": days_remaining,
            "pessimiste_p10": pessimistic_rev,
            "realiste_p50": realistic_rev,
            "optimiste_p90": optimistic_rev,
            "gap_amount": gap_amount,
            "missing_deals_needed": missing_deals,
            "strategic_advice": advice,
            "trajectories_chart": trajectories_chart
        }

if __name__ == "__main__":
    engine = SalesForecastingEngine()
    res = engine.run_monte_carlo_simulation(
        current_revenue=840000,
        target_revenue=1500000,
        days_remaining=14
    )
    print("=== Simulation Monte Carlo des Ventes (1 000 Itérations) ===")
    print(f"Probabilité d'atteindre l'objectif : {res['probability_pct']}%")
    print(f"Projection Réaliste (Médiane) : {res['realiste_p50']:,.0f} FCFA")
    print(f"Conseil Stratégique : {res['strategic_advice']}")
